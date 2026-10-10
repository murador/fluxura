"""Test della validazione XSD FatturaPA."""

import shutil
from pathlib import Path

import pytest

from fluxura.domain.models import InvoiceStatus
from fluxura.services import verification
from fluxura.services.verification import XmlValidationError, validate_xml

FIXTURE = Path(__file__).parent / "fixtures" / "fattura_1.xml"


@pytest.fixture(autouse=True)
def fresh_repo(monkeypatch):
    repo = verification.InvoiceRepository()
    monkeypatch.setattr(verification, "repo", repo)
    return repo


def _copy(tmp_path: Path, invoice_id: int, content: str | None = None) -> Path:
    target = tmp_path / f"fattura_{invoice_id}.xml"
    if content is None:
        shutil.copy(FIXTURE, target)
    else:
        target.write_text(content, encoding="utf-8")
    return target


def test_valid_xml_sets_verificata(tmp_path, fresh_repo):
    assert validate_xml(_copy(tmp_path, 1)) is True
    assert fresh_repo._state[1]["status"] == InvoiceStatus.VERIFICATA.value


def test_missing_required_field(tmp_path, fresh_repo):
    content = FIXTURE.read_text(encoding="utf-8").replace("<Divisa>EUR</Divisa>", "")
    with pytest.raises(XmlValidationError) as exc:
        validate_xml(_copy(tmp_path, 2, content))
    assert exc.value.errors and exc.value.errors[0].line > 0
    state = fresh_repo._state[2]
    assert state["status"] == InvoiceStatus.ERRORE_VALIDAZIONE.value
    assert state["error"]


def test_wrong_type(tmp_path, fresh_repo):
    content = FIXTURE.read_text(encoding="utf-8").replace("<Data>2026-01-15</Data>", "<Data>15/01/2026</Data>")
    with pytest.raises(XmlValidationError):
        validate_xml(_copy(tmp_path, 3, content))
    assert fresh_repo._state[3]["status"] == InvoiceStatus.ERRORE_VALIDAZIONE.value


def test_wrong_element_order(tmp_path):
    content = FIXTURE.read_text(encoding="utf-8").replace(
        "<TipoDocumento>TD01</TipoDocumento>\n        <Divisa>EUR</Divisa>",
        "<Divisa>EUR</Divisa>\n        <TipoDocumento>TD01</TipoDocumento>",
    )
    with pytest.raises(XmlValidationError):
        validate_xml(_copy(tmp_path, 4, content))


def test_malformed_xml(tmp_path, fresh_repo):
    with pytest.raises(XmlValidationError):
        validate_xml(_copy(tmp_path, 5, "<a><b></a>"))
    assert fresh_repo._state[5]["status"] == InvoiceStatus.ERRORE_VALIDAZIONE.value


def test_missing_xsd(tmp_path):
    with pytest.raises(OSError):
        validate_xml(_copy(tmp_path, 6), xsd_path=tmp_path / "nope.xsd")


def test_corrupted_xsd(tmp_path):
    bad = tmp_path / "bad.xsd"
    bad.write_text("<xs:schema", encoding="utf-8")
    with pytest.raises(Exception):
        validate_xml(_copy(tmp_path, 7), xsd_path=bad)


def test_external_entity_not_resolved(tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_text("TOPSECRET", encoding="utf-8")
    content = FIXTURE.read_text(encoding="utf-8").replace(
        "<p:FatturaElettronica",
        f'<!DOCTYPE x [<!ENTITY xxe SYSTEM "{secret.as_uri()}">]>\n<p:FatturaElettronica',
        1,
    ).replace("<Numero>1/2026</Numero>", "<Numero>&xxe;</Numero>")
    path = _copy(tmp_path, 8, content)
    with pytest.raises(XmlValidationError) as exc:
        validate_xml(path)
    assert "TOPSECRET" not in str(exc.value)