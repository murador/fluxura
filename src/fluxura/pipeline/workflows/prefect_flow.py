"""Workflow Prefect equivalente alla pipeline Celery.

Utile quando si desidera orchestrazione osservabile con task/fasi esplicite.
"""

from prefect import flow, task

from fluxura.services.calculation import calculate_totals
from fluxura.services.extraction import extract_invoice
from fluxura.services.pec_sender import send_via_pec
from fluxura.services.verification import request_manual_approval, validate_xml
from fluxura.services.xml_generation import generate_fatturapa_xml


@task
def estrazione(invoice_id: int):
    """Recupera i dati della fattura dal repository."""
    return extract_invoice(invoice_id)


@task
def calcolo(payload):
    """Calcola i totali economici a partire dal payload estratto."""
    return calculate_totals(payload)


@task
def generazione(data):
    """Produce il file XML FatturaPA su filesystem."""
    return generate_fatturapa_xml(data)


@task
def verifica(xml_path):
    """Combina controlli automatici e approvazione umana prima dell'invio."""
    return validate_xml(xml_path) and request_manual_approval(xml_path)


@task
def invio_pec(xml_path):
    """Inoltra il file XML tramite canale PEC."""
    send_via_pec(xml_path)


@flow(name="pipeline-fatturapa")
def pipeline_fattura(invoice_id: int):
    """Definisce la dipendenza sequenziale tra tutti i task Prefect."""
    payload = estrazione(invoice_id)
    data = calcolo(payload)
    xml_path = generazione(data)
    approved = verifica(xml_path)
    if approved:
        invio_pec(xml_path)
