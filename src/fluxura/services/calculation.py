"""Servizio di calcolo importi fiscali per la fattura."""

from fluxura.domain.models import InvoicePayload, InvoiceStatus
from fluxura.infrastructure.repository import InvoiceRepository

repo = InvoiceRepository()


def calculate_totals(payload: InvoicePayload) -> dict:
    """Calcola imponibile, IVA e totale aggregando tutte le righe fattura."""
    imponibile = 0.0
    iva = 0.0

    for line in payload.linee:
        # Applica lo sconto percentuale al prezzo unitario della riga.
        prezzo_scontato = line.prezzo_unitario * (1 - line.sconto_percentuale / 100)
        # Calcola base imponibile riga: prezzo scontato * quantità.
        imponibile_linea = prezzo_scontato * line.quantita
        # Calcola imposta riga in base all'aliquota IVA.
        iva_linea = imponibile_linea * line.aliquota_iva / 100
        # Accumula nei totali documento.
        imponibile += imponibile_linea
        iva += iva_linea

    totale = imponibile + iva
    repo.set_status(payload.invoice_id, InvoiceStatus.CALCOLATA)
    return {
        "payload": payload.to_dict(),
        "totali": {
            "imponibile": round(imponibile, 2),
            "iva": round(iva, 2),
            "totale": round(totale, 2),
        },
    }
