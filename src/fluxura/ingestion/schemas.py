"""Schemi di validazione per le fatture ricevute via REST (JSON)."""

from datetime import date

from pydantic import BaseModel, Field

from fluxura.domain.models import InvoiceLine, InvoicePayload


class PartyIn(BaseModel):
    denominazione: str
    piva: str
    indirizzo: str
    cap: str
    comune: str
    provincia: str
    codice_destinatario: str | None = None


class LineIn(BaseModel):
    descrizione: str
    quantita: float = Field(gt=0)
    prezzo_unitario: float = Field(ge=0)
    aliquota_iva: float = Field(ge=0, le=100)
    sconto_percentuale: float = Field(default=0.0, ge=0, le=100)


class InvoiceIn(BaseModel):
    """Corpo JSON accettato dall'endpoint di ingestione."""

    invoice_id: int
    numero_fattura: str
    data: date | None = None
    cedente: PartyIn
    destinatario: PartyIn
    linee: list[LineIn] = Field(min_length=1)

    def to_payload(self) -> InvoicePayload:
        return InvoicePayload(
            invoice_id=self.invoice_id,
            cedente=self.cedente.model_dump(exclude_none=True),
            destinatario=self.destinatario.model_dump(exclude_none=True),
            numero_fattura=self.numero_fattura,
            data=self.data or date.today(),
            linee=[InvoiceLine(**linea.model_dump()) for linea in self.linee],
        )
