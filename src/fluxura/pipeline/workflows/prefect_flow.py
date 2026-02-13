from prefect import flow, task

from fluxura.services.calculation import calculate_totals
from fluxura.services.extraction import extract_invoice
from fluxura.services.pec_sender import send_via_pec
from fluxura.services.verification import request_manual_approval, validate_xml
from fluxura.services.xml_generation import generate_fatturapa_xml


@task
def estrazione(invoice_id: int):
    return extract_invoice(invoice_id)


@task
def calcolo(payload):
    return calculate_totals(payload)


@task
def generazione(data):
    return generate_fatturapa_xml(data)


@task
def verifica(xml_path):
    return validate_xml(xml_path) and request_manual_approval(xml_path)


@task
def invio_pec(xml_path):
    send_via_pec(xml_path)


@flow(name="pipeline-fatturapa")
def pipeline_fattura(invoice_id: int):
    payload = estrazione(invoice_id)
    data = calcolo(payload)
    xml_path = generazione(data)
    approved = verifica(xml_path)
    if approved:
        invio_pec(xml_path)
