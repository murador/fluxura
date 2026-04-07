"""Modelli di dominio della pipeline fatture.

Qui sono definiti i tipi principali scambiati tra i vari servizi: stato
fattura, riga fattura e payload complessivo.
"""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class InvoiceStatus(StrEnum):
    """Stati logici del ciclo di vita di una fattura nella pipeline."""

    ESTRATTA = "estratta"
    CALCOLATA = "calcolata"
    XML_GENERATO = "xml_generato"
    VERIFICATA = "verificata"
    INVIATA = "inviata"
    ERRORE = "errore"


@dataclass(slots=True)
class InvoiceLine:
    """Rappresenta una singola riga economica della fattura."""

    descrizione: str
    quantita: float
    prezzo_unitario: float
    aliquota_iva: float
    sconto_percentuale: float = 0.0

    def to_dict(self) -> dict:
        """Serializza la riga in un dizionario JSON-friendly."""
        return {
            "descrizione": self.descrizione,
            "quantita": self.quantita,
            "prezzo_unitario": self.prezzo_unitario,
            "aliquota_iva": self.aliquota_iva,
            "sconto_percentuale": self.sconto_percentuale,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "InvoiceLine":
        """Ricostruisce ``InvoiceLine`` da un dizionario serializzato."""
        return cls(**data)


@dataclass(slots=True)
class InvoicePayload:
    """Payload completo della fattura lungo le fasi di orchestrazione."""

    invoice_id: int
    cedente: dict
    destinatario: dict
    numero_fattura: str
    data: date
    linee: list[InvoiceLine]

    def to_dict(self) -> dict:
        """Converte il payload in formato serializzabile su code/task queue."""
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
        """Deserializza il payload rigenerando anche le righe tipizzate."""
        return cls(
            invoice_id=data["invoice_id"],
            cedente=data["cedente"],
            destinatario=data["destinatario"],
            numero_fattura=data["numero_fattura"],
            data=date.fromisoformat(data["data"]),
            linee=[InvoiceLine.from_dict(linea) for linea in data["linee"]],
        )
