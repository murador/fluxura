from fluxura.domain.models import InvoicePayload, InvoiceStatus
from fluxura.infrastructure.repository import InvoiceRepository

repo = InvoiceRepository()


def calculate_totals(payload: InvoicePayload) -> dict:
    imponibile = 0.0
    iva = 0.0

    for line in payload.linee:
        prezzo_scontato = line.prezzo_unitario * (1 - line.sconto_percentuale / 100)
        imponibile_linea = prezzo_scontato * line.quantita
        iva_linea = imponibile_linea * line.aliquota_iva / 100
        imponibile += imponibile_linea
        iva += iva_linea

    totale = imponibile + iva
    repo.set_status(payload.invoice_id, InvoiceStatus.CALCOLATA)
    return {
        "payload": payload,
        "totali": {
            "imponibile": round(imponibile, 2),
            "iva": round(iva, 2),
            "totale": round(totale, 2),
        },
    }
