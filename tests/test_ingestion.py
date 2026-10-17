from datetime import date
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, insert

from fluxura.api import app as api_module
from fluxura.ingestion.sources import (
    InvoiceNotFound,
    JsonInvoiceSource,
    PostgresInvoiceSource,
    invoice_lines_table,
    invoices_table,
    metadata,
)

PARTY = {"denominazione": "A", "piva": "01234567890", "indirizzo": "Via 1", "cap": "00100", "comune": "Roma", "provincia": "RM"}
MESSAGE = {
    "invoice_id": 5,
    "numero_fattura": "5/2026",
    "cedente": PARTY,
    "destinatario": {**PARTY, "codice_destinatario": "ABC1234"},
    "linee": [{"descrizione": "x", "quantita": 2, "prezzo_unitario": 10, "aliquota_iva": 22}],
}


def test_json_source_builds_payload():
    payload = JsonInvoiceSource().load(MESSAGE)
    assert payload.invoice_id == 5
    assert payload.data == date.today()
    assert payload.linee[0].sconto_percentuale == 0.0


def test_postgres_source_reads_invoice():
    engine = create_engine("sqlite://")
    metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(
            insert(invoices_table).values(
                id=1, numero_fattura="1/2026", data=date(2026, 1, 2), cedente=PARTY, destinatario=PARTY
            )
        )
        conn.execute(
            insert(invoice_lines_table).values(
                invoice_id=1, descrizione="x", quantita=2, prezzo_unitario=10, aliquota_iva=22, sconto_percentuale=0
            )
        )
    source = PostgresInvoiceSource(engine)
    payload = source.load(1)
    assert payload.numero_fattura == "1/2026" and payload.linee[0].quantita == 2.0
    with pytest.raises(InvoiceNotFound):
        source.load(99)


def test_api_json_endpoint(monkeypatch):
    calls = []
    monkeypatch.setattr(api_module, "dispatch_invoice_pipeline", lambda **kw: calls.append(kw) or SimpleNamespace(id="t1"))
    client = TestClient(api_module.app)
    resp = client.post("/invoices", json=MESSAGE)
    assert resp.status_code == 202 and resp.json()["task_id"] == "t1"
    assert calls[0]["payload"]["invoice_id"] == 5
    assert client.post("/invoices", json={"invoice_id": 1}).status_code == 422
