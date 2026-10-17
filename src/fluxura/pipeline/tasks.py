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
    """Estrae una fattura tramite il servizio di estrazione legacy.

    Il task riceve l'identificativo della fattura, delega il caricamento a
    ``extract_invoice`` e converte il ``InvoicePayload`` in un dizionario
    JSON-friendly. Il dizionario è necessario perché Celery deve serializzare
    il risultato per consegnarlo al task successivo.

    Questo task mantiene il punto di ingresso storico della pipeline. I nuovi
    flussi usano invece ``ingest_db_task`` o ``ingest_json_task``, così la
    sorgente (Postgres o REST/JSON) è esplicita già all'avvio della catena.
    """
    return extract_invoice(invoice_id).to_dict()


@celery_app.task(name="fluxura.calculate")
def calculation_task(payload_data: dict) -> dict:
    """Calcola gli importi fiscali della fattura.

    Celery passa al task il dizionario prodotto dal caricamento precedente.
    ``InvoicePayload.from_dict`` ricostruisce il modello di dominio, incluse
    la data e le righe tipizzate; ``calculate_totals`` calcola imponibile, IVA
    e totale applicando quantità, prezzi e sconti delle righe.

    Il risultato resta un dizionario serializzabile, che diventa l'input del
    task di generazione XML.
    """
    payload = InvoicePayload.from_dict(payload_data)
    return calculate_totals(payload)


@celery_app.task(name="fluxura.generate_xml")
def generation_task(data: dict) -> str:
    """Genera il documento XML FatturaPA.

    Riceve i dati economici calcolati, invoca il servizio che costruisce
    l'XML conforme allo schema FatturaPA e restituisce il percorso del file.
    Il percorso viene convertito in ``str`` perché gli oggetti ``Path`` non
    sono necessariamente serializzabili dal serializer configurato per
    Celery.
    """
    xml_path = generate_fatturapa_xml(data)
    return str(xml_path)


@celery_app.task(name="fluxura.verify")
def verification_task(xml_path: str) -> str:
    """Valida e sottopone il documento all'approvazione prima dell'invio.

    Il percorso ricevuto dalla catena viene trasformato in ``Path`` e
    sottoposto a due controlli consecutivi:

    1. ``validate_xml`` verifica la conformità tecnica al formato previsto;
    2. ``request_manual_approval`` rappresenta il passaggio di approvazione
       funzionale/manuale.

    L'invio viene consentito solo se entrambi i controlli restituiscono
    ``True``. In caso contrario il task solleva ``ValueError``: la catena
    Celery si interrompe e ``pec_sending_task`` non viene eseguito.
    """
    path = __import__("pathlib").Path(xml_path)
    if validate_xml(path) and request_manual_approval(path):
        return xml_path
    raise ValueError("Verifica non superata")


@celery_app.task(name="fluxura.send_pec")
def pec_sending_task(xml_path: str) -> str:
    """Invia il documento approvato tramite il canale PEC.

    Il task riceve il percorso già verificato, lo converte in ``Path`` e
    delega l'invio a ``send_via_pec``. Se il servizio termina correttamente,
    ripropaga il percorso originale come risultato Celery; questo conserva
    un riferimento semplice al documento per audit o task successivi.
    """
    path = __import__("pathlib").Path(xml_path)
    send_via_pec(path)
    return xml_path


@celery_app.task(name="fluxura.ingest_db")
def ingest_db_task(invoice_id: int) -> dict:
    """Carica una fattura da Postgres e la prepara per la pipeline.

    Questo è il primo task del flusso avviato con ``invoice_id``. La sorgente
    ``PostgresInvoiceSource`` legge la testata e le righe e restituisce un
    ``InvoicePayload``. Il payload viene quindi serializzato in un dizionario
    per il passaggio attraverso la coda Celery.

    Lo stato viene marcato come ``ESTRATTA`` dopo il caricamento riuscito.
    Se la fattura non esiste o non contiene righe, la sorgente solleva
    ``InvoiceNotFound`` e il task fallisce senza produrre un payload parziale.
    """
    payload = PostgresInvoiceSource().load(invoice_id)
    InvoiceRepository().set_status(invoice_id, InvoiceStatus.ESTRATTA)
    return payload.to_dict()


@celery_app.task(name="fluxura.ingest_json")
def ingest_json_task(message: dict) -> dict:
    """Valida un messaggio JSON REST e lo prepara per la pipeline.

    Il messaggio è il dizionario ricevuto dall'API Gateway. La sorgente
    ``JsonInvoiceSource`` lo valida tramite ``InvoiceIn`` e costruisce il
    modello di dominio ``InvoicePayload``. La validazione impedisce che dati
    incompleti o fuori dai limiti ammessi entrino nei task fiscali.

    Dopo la validazione riuscita, lo stato della fattura viene marcato come
    ``ESTRATTA`` e il payload viene serializzato per Celery.
    """
    payload = JsonInvoiceSource().load(message)
    InvoiceRepository().set_status(payload.invoice_id, InvoiceStatus.ESTRATTA)
    return payload.to_dict()


def dispatch_invoice_pipeline(invoice_id: int | None = None, payload: dict | None = None):
    """Avvia la pipeline asincrona scegliendo la sorgente della fattura.

    Args:
        invoice_id: Identificativo della fattura da caricare da Postgres.
            Viene usato quando la pipeline deve partire dal database.
        payload: Dizionario JSON già ricevuto dal punto di ingresso REST.
            Viene usato quando i dati della fattura sono già disponibili nel
            messaggio e non devono essere riletti dal database.

    La funzione richiede esattamente uno dei due argomenti. Questa regola
    evita sia una richiesta ambigua, sia l'avvio di una catena senza dati.
    In base alla sorgente seleziona il primo task:

    - ``ingest_db_task`` per ``invoice_id``;
    - ``ingest_json_task`` per ``payload``.

    Dopo il caricamento, ``chain`` collega i task con la firma ``.s()``:
    il risultato del task precedente viene passato automaticamente come
    primo argomento al task successivo. L'ordine effettivo è:

    ``ingest -> calcolo -> generazione XML -> verifica/approvazione -> PEC``.

    ``apply_async`` pubblica la catena sul broker Celery e restituisce
    immediatamente un ``AsyncResult``. La funzione quindi non attende la
    conclusione della pipeline e non esegue direttamente i task nel processo
    dell'API.

    Raises:
        ValueError: se vengono forniti entrambi gli argomenti oppure nessuno.
    """
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
