from pathlib import Path

from lxml import etree

from fluxura.domain.models import InvoiceStatus
from fluxura.infrastructure.repository import InvoiceRepository

repo = InvoiceRepository()


def validate_xml(xml_path: Path, xsd_path: Path | None = None) -> bool:
    if xsd_path is None:
        # Stub: in produzione puntare al file XSD ufficiale.
        repo.set_status(_invoice_id_from_path(xml_path), InvoiceStatus.VERIFICATA)
        return True

    xml_doc = etree.parse(str(xml_path))
    schema_doc = etree.parse(str(xsd_path))
    schema = etree.XMLSchema(schema_doc)
    schema.assertValid(xml_doc)
    repo.set_status(_invoice_id_from_path(xml_path), InvoiceStatus.VERIFICATA)
    return True


def request_manual_approval(xml_path: Path) -> bool:
    # Hook per dashboard/web UI.
    return True


def _invoice_id_from_path(xml_path: Path) -> int:
    return int(xml_path.stem.split("_")[-1])
