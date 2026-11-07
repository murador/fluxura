"""
fluxura.ingestion.schemas
========================
Schemi di validazione per le fatture ricevute via REST (JSON).
Descrizione dei campi e delle regole di validazione per le fatture
ricevute via REST (JSON).
"""

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
    # Impedisce righe senza quantità e prezzi negativi già al confine REST.
    # La quantità deve essere positiva e non zero.
    quantita: float = Field(gt=0)
    # Il prezzo unitario non può essere negativo o zero.
    prezzo_unitario: float = Field(ge=0)
    # L'aliquota e lo sconto sono percentuali: 
    # entrambi devono restare nel range 0-100.
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
        # Mantiene assenti i campi opzionali invece di trasformarli in valori nulli.
        return InvoicePayload(
            invoice_id=self.invoice_id,
            cedente=self.cedente.model_dump(exclude_none=True),
            destinatario=self.destinatario.model_dump(exclude_none=True),
            numero_fattura=self.numero_fattura,
            # La data può mancare nella richiesta;
            # in quel caso si usa la data corrente.
            data=self.data or date.today(),
            # I modelli REST validano l'input; le righe vengono poi convertite
            # nel tipo previsto dal dominio prima di costruire il payload.
            linee=[InvoiceLine(**linea.model_dump()) for linea in self.linee],
        )
