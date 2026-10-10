"""Servizi di verifica tecnica e approvazione manuale XML."""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from lxml import etree

from fluxura.config import settings
from fluxura.domain.models import InvoiceStatus
from fluxura.infrastructure.repository import InvoiceRepository

repo = InvoiceRepository()

DEFAULT_XSD_PATH = (
    Path(__file__).resolve().parents[1]
    / "schemas"
    / "fatturapa"
    / "Schema_del_file_xml_FatturaPA_v1.2.2.xsd"
)


@dataclass(frozen=True, slots=True)
class XsdError:
    """Singolo errore di validazione con posizione nel documento."""

    line: int
    column: int
    message: str
    path: str

    def __str__(self) -> str:
        return f"riga {self.line}, colonna {self.column}: {self.message} ({self.path})"


class XmlValidationError(ValueError):
    """XML non conforme allo schema XSD (o non well-formed)."""

    def __init__(self, errors: list[XsdError]):
        self.errors = errors
        super().__init__("; ".join(str(e) for e in errors))


def resolve_xsd_path(xsd_path: Path | None = None) -> Path:
    """Sceglie l'XSD: argomento esplicito, poi settings, poi schema incluso."""
    if xsd_path is not None:
        return xsd_path
    if settings.xsd_path:
        return Path(settings.xsd_path)
    return DEFAULT_XSD_PATH


@lru_cache(maxsize=4)
def _load_schema(xsd_path: str) -> etree.XMLSchema:
    """Carica e cachea lo schema; nessun accesso di rete durante il parsing."""
    parser = etree.XMLParser(no_network=True, resolve_entities=False)
    return etree.XMLSchema(etree.parse(xsd_path, parser))


def validate_xml(xml_path: Path, xsd_path: Path | None = None) -> bool:
    """Valida l'XML contro l'XSD ufficiale e, se conforme, imposta VERIFICATA.

    In caso di errore imposta ERRORE_VALIDAZIONE e solleva ``XmlValidationError``.
    """
    invoice_id = _invoice_id_from_path(xml_path)
    schema = _load_schema(str(resolve_xsd_path(xsd_path)))
    parser = etree.XMLParser(no_network=True, resolve_entities=False)

    try:
        xml_doc = etree.parse(str(xml_path), parser)
    except etree.XMLSyntaxError as exc:
        errors = [
            XsdError(e.line, e.column, e.message, "")
            for e in exc.error_log
        ] or [XsdError(0, 0, str(exc), "")]
        _fail(invoice_id, errors)

    # FatturaPA non usa DTD: rifiutarle chiude la porta a XXE ed entity expansion.
    if xml_doc.docinfo.internalDTD is not None or xml_doc.docinfo.externalDTD is not None:
        _fail(invoice_id, [XsdError(0, 0, "DTD/entità non ammesse nel documento", "")])

    if not schema.validate(xml_doc):
        _fail(
            invoice_id,
            [XsdError(e.line, e.column, e.message, e.path or "") for e in schema.error_log],
        )

    repo.set_status(invoice_id, InvoiceStatus.VERIFICATA)
    return True


def _fail(invoice_id: int, errors: list[XsdError]) -> None:
    error = XmlValidationError(errors)
    repo.set_status(invoice_id, InvoiceStatus.ERRORE_VALIDAZIONE, error=str(error))
    raise error


def request_manual_approval(xml_path: Path) -> bool:
    """Hook di approvazione umana: sempre true in questa implementazione demo."""
    # Hook per dashboard/web UI.
    return True


def _invoice_id_from_path(xml_path: Path) -> int:
    """Estrae invoice_id dal nome file atteso: ``fattura_<id>.xml``."""
    return int(xml_path.stem.split("_")[-1])