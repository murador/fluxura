"""Punti di caricamento (sorgenti) delle fatture: Postgres e JSON/REST."""

from typing import Protocol

from sqlalchemy import JSON, Column, Date, ForeignKey, Integer, MetaData, Numeric, String, Table, select
from sqlalchemy.engine import Engine

from fluxura.domain.models import InvoiceLine, InvoicePayload
from fluxura.ingestion.schemas import InvoiceIn

metadata = MetaData()

invoices_table = Table(
    "invoices",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("numero_fattura", String, nullable=False),
    Column("data", Date, nullable=False),
    Column("cedente", JSON, nullable=False),
    Column("destinatario", JSON, nullable=False),
)

invoice_lines_table = Table(
    "invoice_lines",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("invoice_id", Integer, ForeignKey("invoices.id"), nullable=False),
    Column("descrizione", String, nullable=False),
    Column("quantita", Numeric, nullable=False),
    Column("prezzo_unitario", Numeric, nullable=False),
    Column("aliquota_iva", Numeric, nullable=False),
    Column("sconto_percentuale", Numeric, nullable=False, server_default="0"),
)


class InvoiceNotFound(LookupError):
    """La fattura richiesta non esiste nella sorgente."""


class InvoiceSource(Protocol):
    """Contratto comune: ogni sorgente produce un ``InvoicePayload``."""

    def load(self, ref: int | dict) -> InvoicePayload: ...


class PostgresInvoiceSource:
    """Legge una fattura (testata + righe) dal database Postgres."""

    def __init__(self, engine: Engine | None = None):
        if engine is None:
            from fluxura.infrastructure.db import engine as default_engine

            engine = default_engine
        self._engine = engine

    def load(self, invoice_id: int) -> InvoicePayload:
        with self._engine.connect() as conn:
            head = conn.execute(select(invoices_table).where(invoices_table.c.id == invoice_id)).mappings().first()
            if head is None:
                raise InvoiceNotFound(f"Fattura {invoice_id} non trovata")
            rows = (
                conn.execute(
                    select(invoice_lines_table)
                    .where(invoice_lines_table.c.invoice_id == invoice_id)
                    .order_by(invoice_lines_table.c.id)
                )
                .mappings()
                .all()
            )
        if not rows:
            raise InvoiceNotFound(f"Fattura {invoice_id} senza righe")
        return InvoicePayload(
            invoice_id=invoice_id,
            cedente=head["cedente"],
            destinatario=head["destinatario"],
            numero_fattura=head["numero_fattura"],
            data=head["data"],
            linee=[
                InvoiceLine(
                    descrizione=r["descrizione"],
                    quantita=float(r["quantita"]),
                    prezzo_unitario=float(r["prezzo_unitario"]),
                    aliquota_iva=float(r["aliquota_iva"]),
                    sconto_percentuale=float(r["sconto_percentuale"]),
                )
                for r in rows
            ],
        )


class JsonInvoiceSource:
    """Costruisce il payload da un messaggio JSON (già deserializzato in dict)."""

    def load(self, message: dict) -> InvoicePayload:
        return InvoiceIn.model_validate(message).to_payload()
