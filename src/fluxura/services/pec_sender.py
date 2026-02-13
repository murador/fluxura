from pathlib import Path

from fluxura.domain.models import InvoiceStatus
from fluxura.infrastructure.repository import InvoiceRepository

repo = InvoiceRepository()


def send_via_pec(xml_path: Path) -> None:
    invoice_id = int(xml_path.stem.split("_")[-1])
    # Stub: integrazione futura con PEC API / SMTP / SDI.
    repo.set_status(invoice_id, InvoiceStatus.INVIATA)
