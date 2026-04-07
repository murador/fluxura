"""Servizi di verifica tecnica e approvazione manuale XML."""

from pathlib import Path

from lxml import etree

from fluxura.domain.models import InvoiceStatus
from fluxura.infrastructure.repository import InvoiceRepository

repo = InvoiceRepository()


def validate_xml(xml_path: Path, xsd_path: Path | None = None) -> bool:
    """Valida XML contro XSD (se presente) e aggiorna lo stato a verificata."""
    if xsd_path is None:
        # Modalità stub: nessuna validazione schema, solo avanzamento stato.
        repo.set_status(_invoice_id_from_path(xml_path), InvoiceStatus.VERIFICATA)
        return True

    # Parsing documenti XML/XSD e validazione strutturale con lxml.
    xml_doc = etree.parse(str(xml_path))
    schema_doc = etree.parse(str(xsd_path))
    schema = etree.XMLSchema(schema_doc)
    schema.assertValid(xml_doc)
    repo.set_status(_invoice_id_from_path(xml_path), InvoiceStatus.VERIFICATA)
    return True


def request_manual_approval(xml_path: Path) -> bool:
    """Hook di approvazione umana: sempre true in questa implementazione demo."""
    # Hook per dashboard/web UI.
    return True


def _invoice_id_from_path(xml_path: Path) -> int:
    """Estrae invoice_id dal nome file atteso: ``fattura_<id>.xml``."""
    return int(xml_path.stem.split("_")[-1])
