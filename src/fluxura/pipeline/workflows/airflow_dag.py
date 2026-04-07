"""DAG opzionale per orchestrare la stessa pipeline in Airflow."""

from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator

from fluxura.services.calculation import calculate_totals
from fluxura.services.extraction import extract_invoice
from fluxura.services.pec_sender import send_via_pec
from fluxura.services.verification import request_manual_approval, validate_xml
from fluxura.services.xml_generation import generate_fatturapa_xml


def _extract(**context):
    """Estrae la fattura e salva il risultato in XCom con chiave ``payload``."""
    context["ti"].xcom_push(key="payload", value=extract_invoice(context["params"]["invoice_id"]))


def _calculate(**context):
    """Legge il payload da XCom, calcola i totali e risalva in XCom."""
    payload = context["ti"].xcom_pull(key="payload")
    context["ti"].xcom_push(key="calculated", value=calculate_totals(payload))


def _generate(**context):
    """Genera XML e pubblica il percorso del file (stringa) su XCom."""
    data = context["ti"].xcom_pull(key="calculated")
    context["ti"].xcom_push(key="xml", value=str(generate_fatturapa_xml(data)))


def _verify(**context):
    """Valida/approva il file XML; in caso negativo fallisce esplicitamente il task."""
    from pathlib import Path

    xml_path = Path(context["ti"].xcom_pull(key="xml"))
    if not (validate_xml(xml_path) and request_manual_approval(xml_path)):
        raise ValueError("XML non approvato")


def _send(**context):
    """Invia l'XML via PEC leggendo il path prodotto dallo step precedente."""
    from pathlib import Path

    send_via_pec(Path(context["ti"].xcom_pull(key="xml")))


# Definizione DAG: un'unica esecuzione su richiesta (schedule=None), senza catchup.
with DAG(
    dag_id="fluxura_fatturapa_pipeline",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    params={"invoice_id": 1},
) as dag:
    # Ogni PythonOperator incapsula una fase funzionale della pipeline.
    t1 = PythonOperator(task_id="estrazione", python_callable=_extract)
    t2 = PythonOperator(task_id="calcolo", python_callable=_calculate)
    t3 = PythonOperator(task_id="generazione", python_callable=_generate)
    t4 = PythonOperator(task_id="verifica", python_callable=_verify)
    t5 = PythonOperator(task_id="invio_pec", python_callable=_send)

    # Ordinamento rigoroso: la fase successiva parte solo se la precedente è ok.
    t1 >> t2 >> t3 >> t4 >> t5
