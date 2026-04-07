"""Servizio di estrazione dati fattura dal repository sorgente."""

from datetime import date

from fluxura.domain.models import InvoiceLine, InvoicePayload, InvoiceStatus
from fluxura.infrastructure.repository import InvoiceRepository

# Repository locale usato per recupero dati e tracciamento stato.
repo = InvoiceRepository()


def extract_invoice(invoice_id: int) -> InvoicePayload:
    """Legge la fattura sorgente, costruisce il payload e marca lo stato estratto."""
    raw = repo.load_subject_invoice(invoice_id)
    payload = InvoicePayload(
        invoice_id=invoice_id,
        cedente=raw["cedente"],
        destinatario=raw["destinatario"],
        numero_fattura=raw["numero_fattura"],
        data=date.today(),
        linee=[InvoiceLine(**linea) for linea in raw["linee"]],
    )
    repo.set_status(invoice_id, InvoiceStatus.ESTRATTA)
    return payload
