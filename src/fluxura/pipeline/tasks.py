from celery import chain

from fluxura.celery_app import celery_app
from fluxura.services.calculation import calculate_totals
from fluxura.services.extraction import extract_invoice
from fluxura.services.pec_sender import send_via_pec
from fluxura.services.verification import request_manual_approval, validate_xml
from fluxura.services.xml_generation import generate_fatturapa_xml


@celery_app.task(name="fluxura.extract")
def extraction_task(invoice_id: int) -> dict:
    return extract_invoice(invoice_id).__dict__


@celery_app.task(name="fluxura.calculate")
def calculation_task(payload_data: dict) -> dict:
    # ricostruzione semplificata: pipeline iniziale
    from fluxura.services.extraction import extract_invoice

    payload = extract_invoice(payload_data["invoice_id"])
    return calculate_totals(payload)


@celery_app.task(name="fluxura.generate_xml")
def generation_task(data: dict) -> str:
    xml_path = generate_fatturapa_xml(data)
    return str(xml_path)


@celery_app.task(name="fluxura.verify")
def verification_task(xml_path: str) -> str:
    path = __import__("pathlib").Path(xml_path)
    if validate_xml(path) and request_manual_approval(path):
        return xml_path
    raise ValueError("Verifica non superata")


@celery_app.task(name="fluxura.send_pec")
def pec_sending_task(xml_path: str) -> str:
    path = __import__("pathlib").Path(xml_path)
    send_via_pec(path)
    return xml_path


def dispatch_invoice_pipeline(invoice_id: int):
    return chain(
        extraction_task.s(invoice_id),
        calculation_task.s(),
        generation_task.s(),
        verification_task.s(),
        pec_sending_task.s(),
    ).apply_async()
