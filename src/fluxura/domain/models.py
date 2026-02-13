from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class InvoiceStatus(StrEnum):
    ESTRATTA = "estratta"
    CALCOLATA = "calcolata"
    XML_GENERATO = "xml_generato"
    VERIFICATA = "verificata"
    INVIATA = "inviata"
    ERRORE = "errore"


@dataclass(slots=True)
class InvoiceLine:
    descrizione: str
    quantita: float
    prezzo_unitario: float
    aliquota_iva: float
    sconto_percentuale: float = 0.0


@dataclass(slots=True)
class InvoicePayload:
    invoice_id: int
    cedente: dict
    destinatario: dict
    numero_fattura: str
    data: date
    linee: list[InvoiceLine]
