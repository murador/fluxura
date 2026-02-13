from datetime import date

from fluxura.domain.models import InvoiceLine, InvoicePayload, InvoiceStatus
from fluxura.infrastructure.repository import InvoiceRepository


repo = InvoiceRepository()


def extract_invoice(invoice_id: int) -> InvoicePayload:
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
