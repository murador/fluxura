"""Task Celery che compongono la pipeline end-to-end di fatturazione."""

from celery import chain

from fluxura.celery_app import celery_app
from fluxura.domain.models import InvoicePayload, InvoiceStatus
from fluxura.infrastructure.repository import InvoiceRepository
from fluxura.ingestion.sources import JsonInvoiceSource, PostgresInvoiceSource
from fluxura.services.calculation import calculate_totals
from fluxura.services.extraction import extract_invoice
from fluxura.services.pec_sender import send_via_pec
from fluxura.services.verification import request_manual_approval, validate_xml
from fluxura.services.xml_generation import generate_fatturapa_xml


@celery_app.task(name="fluxura.extract")
def extraction_task(invoice_id: int) -> dict:
    """Estrae i dati sorgente della fattura e li serializza per il task successivo."""
    return extract_invoice(invoice_id).to_dict()


@celery_app.task(name="fluxura.calculate")
def calculation_task(payload_data: dict) -> dict:
    """Ricostruisce il payload dal dizionario e calcola imponibile/IVA/totale."""
    payload = InvoicePayload.from_dict(payload_data)
    return calculate_totals(payload)


@celery_app.task(name="fluxura.generate_xml")
def generation_task(data: dict) -> str:
    """Genera l'XML FatturaPA e restituisce il path come stringa serializzabile."""
    xml_path = generate_fatturapa_xml(data)
    return str(xml_path)


@celery_app.task(name="fluxura.verify")
def verification_task(xml_path: str) -> str:
    """Esegue validazione tecnica + approvazione manuale prima dell'invio."""
    path = __import__("pathlib").Path(xml_path)
    if validate_xml(path) and request_manual_approval(path):
        return xml_path
    raise ValueError("Verifica non superata")


@celery_app.task(name="fluxura.send_pec")
def pec_sending_task(xml_path: str) -> str:
    """Invia il documento tramite PEC e propaga il path per eventuali audit."""
    path = __import__("pathlib").Path(xml_path)
    send_via_pec(path)
    return xml_path


@celery_app.task(name="fluxura.ingest_db")
def ingest_db_task(invoice_id: int) -> dict:
    """Punto di caricamento Postgres: legge la fattura dal database."""
    payload = PostgresInvoiceSource().load(invoice_id)
    InvoiceRepository().set_status(invoice_id, InvoiceStatus.ESTRATTA)
    return payload.to_dict()


@celery_app.task(name="fluxura.ingest_json")
def ingest_json_task(message: dict) -> dict:
    """Punto di caricamento REST: valida il messaggio JSON e produce il payload."""
    payload = JsonInvoiceSource().load(message)
    InvoiceRepository().set_status(payload.invoice_id, InvoiceStatus.ESTRATTA)
    return payload.to_dict()


def dispatch_invoice_pipeline(invoice_id: int | None = None, payload: dict | None = None):
    """Lancia la catena Celery partendo da Postgres (``invoice_id``) o da JSON (``payload``)."""
    if (invoice_id is None) == (payload is None):
        raise ValueError("Specificare esattamente uno tra invoice_id e payload")
    first = ingest_db_task.s(invoice_id) if payload is None else ingest_json_task.s(payload)
    return chain(
        first,
        calculation_task.s(),
        generation_task.s(),
        verification_task.s(),
        pec_sending_task.s(),
    ).apply_async()
