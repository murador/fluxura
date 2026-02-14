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

    def to_dict(self) -> dict:
        return {
            "descrizione": self.descrizione,
            "quantita": self.quantita,
            "prezzo_unitario": self.prezzo_unitario,
            "aliquota_iva": self.aliquota_iva,
            "sconto_percentuale": self.sconto_percentuale,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "InvoiceLine":
        return cls(**data)


@dataclass(slots=True)
class InvoicePayload:
    invoice_id: int
    cedente: dict
    destinatario: dict
    numero_fattura: str
    data: date
    linee: list[InvoiceLine]

    def to_dict(self) -> dict:
        return {
            "invoice_id": self.invoice_id,
            "cedente": self.cedente,
            "destinatario": self.destinatario,
            "numero_fattura": self.numero_fattura,
            "data": self.data.isoformat(),
            "linee": [linea.to_dict() for linea in self.linee],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "InvoicePayload":
        return cls(
            invoice_id=data["invoice_id"],
            cedente=data["cedente"],
            destinatario=data["destinatario"],
            numero_fattura=data["numero_fattura"],
            data=date.fromisoformat(data["data"]),
            linee=[InvoiceLine.from_dict(linea) for linea in data["linee"]],
        )
