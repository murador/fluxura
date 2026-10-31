# Architettura di Fluxura

## 1. Scopo e stato dell'implementazione

Fluxura è un'applicazione Python organizzata come pipeline asincrona per
acquisire fatture, calcolarne gli importi, produrre XML FatturaPA, verificarlo
e inoltrarlo attraverso un canale PEC. Il flusso principale è composto da
servizi separati e coordinato da task Celery; FastAPI espone i punti di
ingresso HTTP.

Il repository contiene una vertical slice dimostrativa, non un servizio
produttivo completo. In particolare, il repository che registra gli stati è
in memoria, il passaggio di approvazione manuale è un hook sempre positivo e
il mittente PEC non effettua un invio di rete. Queste differenze sono
importanti per interpretare correttamente quanto segue.

## 2. Vista d'insieme

```text
Client
  │ HTTP / JSON
  ▼
FastAPI (fluxura.api.app)
  ├─ POST /invoices ───────────► validazione Pydantic
  └─ POST /invoices/{id}/process ► controllo fattura in Postgres
                                      │
                                      ▼
                              Celery broker (Redis predefinito)
                                      │
                                      ▼
                               Worker Celery
                                      │
                 ingestione → calcolo → XML → verifica → PEC
                                      │
                    ┌─────────────────┴─────────────────┐
                    ▼                                   ▼
             PostgreSQL sorgente              artifacts/xml (filesystem)
             (testata e righe)                (XML generati)
```

Il broker trasporta task e risultati serializzati in JSON. PostgreSQL fornisce
la sorgente opzionale delle fatture; non è ancora il repository persistente
dello stato di avanzamento. I file XML sono scritti sul filesystem del worker.
Perciò un'installazione con più worker deve condividere o rendere persistente
la directory di output se i task successivi possono essere eseguiti su nodi
diversi.

## 3. Moduli e responsabilità

| Area | Modulo | Responsabilità e relazione con gli altri moduli |
| --- | --- | --- |
| API | `src/fluxura/api/app.py` | Espone gli endpoint FastAPI. Valida e accetta le richieste, quindi delega l'esecuzione a `dispatch_invoice_pipeline`; non esegue il flusso sincronicamente. |
| Ingestione | `src/fluxura/ingestion/schemas.py` | Definisce i modelli Pydantic dell'input REST, inclusi vincoli su quantità, aliquota, sconto e presenza di almeno una riga. Converte i dati validati nel modello di dominio. |
| Ingestione | `src/fluxura/ingestion/sources.py` | Definisce il contratto `InvoiceSource` e le implementazioni JSON e PostgreSQL. La sorgente DB legge testata e righe e produce lo stesso `InvoicePayload` utilizzato dal resto del flusso. |
| Dominio | `src/fluxura/domain/models.py` | Definisce `InvoiceLine`, `InvoicePayload` e `InvoiceStatus`, cioè i dati condivisi e gli stati logici della fattura. `to_dict`/`from_dict` rendono il payload trasferibile tra task Celery. |
| Pipeline | `src/fluxura/pipeline/tasks.py` | Contiene i task Celery e compone la catena asincrona. Ogni fase riceve il risultato serializzabile della fase precedente. |
| Servizi | `src/fluxura/services/extraction.py` | Percorso di estrazione legacy: usa il repository demo/in-memory e crea un payload. Non è il percorso Postgres usato dai task `ingest_db_task`. |
| Servizi | `src/fluxura/services/calculation.py` | Calcola imponibile, IVA e totale applicando sconti e quantità. Restituisce il payload insieme ai totali. |
| Servizi | `src/fluxura/services/xml_generation.py` | Genera il tracciato FPR12 a partire dal payload e dai totali, aggrega imponibili per aliquota IVA e salva l'XML nella directory configurata. |
| Servizi | `src/fluxura/services/verification.py` | Valida l'XML contro lo schema XSD locale, registra errori di validazione e fornisce il punto di aggancio per l'approvazione umana. |
| Servizi | `src/fluxura/services/pec_sender.py` | Punto di integrazione del canale PEC. Nell'implementazione attuale marca la fattura come inviata, senza trasmettere il file. |
| Persistenza | `src/fluxura/infrastructure/db.py` | Crea l'engine SQLAlchemy e la factory di sessioni usando la configurazione; costituisce la base per l'accesso al database. |
| Persistenza | `src/fluxura/infrastructure/repository.py` | Implementa lo stato volatile in memoria e un dataset dimostrativo di fallback. Non salva stato o errori in PostgreSQL. |
| Configurazione | `src/fluxura/config.py`, `src/fluxura/celery_app.py` | Caricano la configurazione runtime e inizializzano Celery con broker, backend e serializzazione JSON. |
| Formati | `src/fluxura/schemas/fatturapa/` | Include gli XSD usati per la validazione offline. Gli hash sono controllati dai test. |

### Contratti principali

- Le sorgenti producono un `InvoicePayload`, indipendentemente dal canale di
  ingresso.
- Il payload serializzato contiene `invoice_id`, anagrafiche, numero, data
  ISO-8601 e righe; questo è il contratto trasferito attraverso Celery.
- Il calcolo aggiunge la struttura `totali` con `imponibile`, `iva` e
  `totale`. La generazione XML usa sia il payload sia i dati economici.
- Tra task Celery si passano dizionari JSON o stringhe (ad esempio il percorso
  dell'XML), non sessioni DB o oggetti non serializzabili.

## 4. Flusso end-to-end implementato

### 4.1 Ingresso e selezione della sorgente

1. `POST /invoices` riceve JSON. FastAPI/Pydantic valida il corpo e l'API
   passa il payload serializzato a Celery.
2. `POST /invoices/{invoice_id}/process` verifica prima che la fattura e le
   sue righe siano leggibili da PostgreSQL; se non esistono restituisce 404.
   In seguito accoda il solo identificativo. Il task di ingestione carica
   nuovamente la fattura dal database.
3. `dispatch_invoice_pipeline` richiede esattamente una sorgente: `invoice_id`
   oppure `payload`. Se ne seleziona il task di ingestione corrispondente e
   pubblica la catena in modo asincrono.

### 4.2 Elaborazione

La catena Celery principale è:

```text
ingest_db / ingest_json
  → calculation
  → generate_xml
  → verify (XSD e approvazione)
  → send_pec
```

- **Ingestione**: produce il payload di dominio. La sorgente JSON applica la
  validazione Pydantic; la sorgente PostgreSQL legge testata e righe dalle
  tabelle `invoices` e `invoice_lines`.
- **Calcolo**: calcola gli importi applicando lo sconto alla riga, poi quantità
  e aliquota IVA. I risultati monetari vengono arrotondati a due decimali.
- **Generazione**: costruisce l'XML FatturaPA FPR12, lo scrive come
  `fattura_<invoice_id>.xml` sotto `FLUXURA_INVOICE_OUTPUT_DIR` e restituisce
  il percorso.
- **Verifica**: carica lo schema XSD locale con parsing senza rete e rifiuta
  documenti malformati, non conformi o con DTD. Se la validazione fallisce,
  solleva un errore e Celery non esegue il task PEC. L'hook
  `request_manual_approval` restituisce sempre `True` nella versione attuale.
- **Invio**: `send_via_pec` al momento non contatta PEC, SMTP o SDI; aggiorna
  soltanto lo stato in memoria.

## 5. Stato e persistenza: limiti attuali

`InvoiceStatus` modella le fasi `estratta`, `calcolata`, `xml_generato`,
`verificata`, `errore_validazione`, `inviata` ed `errore`. I servizi aggiornano
lo stato tramite `InvoiceRepository`, ma ogni servizio/task crea o importa
istanze di repository in memoria. Di conseguenza:

- gli stati non sono condivisi in modo affidabile tra processi o worker e
  scompaiono al riavvio;
- `db.py` configura SQLAlchemy, ma il repository di stato non lo usa;
- PostgreSQL è una sorgente di ingresso, non la persistenza del ciclo di vita;
- la definizione delle tabelle in `ingestion/sources.py` e lo script di seed
  servono all'ingestione/demo e non costituiscono un sistema di migrazioni.

Per uso produttivo occorre sostituire il repository volatile con persistenza
transazionale, definire migrazioni e modellare in modo condiviso stati, errori,
tentativi e riferimenti ai documenti.

## 6. Orchestrazione e infrastruttura

### Celery (percorso integrato)

`celery_app.py` legge le URL da `FLUXURA_CELERY_BROKER_URL` e
`FLUXURA_CELERY_RESULT_BACKEND`, accetta solo JSON e configura il fuso
`Europe/Rome`. L'API usa direttamente `dispatch_invoice_pipeline`; i task
vengono eseguiti dai worker. Redis è il broker e il backend predefinito.

RabbitMQ è predisposto nei file Docker Compose e Kubernetes, ma non è il broker
selezionato dalla configurazione fornita. Flower è predisposto per osservare i
task Celery.

### Prefect e Airflow (alternative)

`pipeline/workflows/prefect_flow.py` e `pipeline/workflows/airflow_dag.py`
rappresentano definizioni alternative delle fasi, non vengono invocate
dall'API e non fanno parte della catena Celery primaria. Riutilizzano i servizi
ma alcuni passaggi, come l'estrazione, seguono il percorso legacy del
repository demo. Airflow richiede inoltre un ambiente con il pacchetto Airflow,
che non è incluso tra le dipendenze dichiarate in `pyproject.toml`.

### Esecuzione containerizzata

- `docker-compose.yml` avvia PostgreSQL, Redis, RabbitMQ e Flower; non dichiara
  un servizio API o un worker applicativo.
- Il `Dockerfile` costruisce l'immagine applicativa e avvia un worker Celery.
- I manifesti Kubernetes forniscono PostgreSQL, Redis, RabbitMQ, Flower e un
  worker. Non è definito un Deployment dell'API. Il worker usa Redis tramite
  ConfigMap.
- I manifesti mostrati non configurano persistenza durevole per PostgreSQL o
  condivisione persistente della directory degli XML.

## 7. Configurazione ed esecuzione

Le impostazioni sono lette da variabili d'ambiente con prefisso `FLUXURA_` e,
in sviluppo, dal file `.env`:

| Variabile | Uso |
| --- | --- |
| `FLUXURA_DATABASE_URL` | Connessione SQLAlchemy/PostgreSQL. |
| `FLUXURA_CELERY_BROKER_URL` | Broker Celery (Redis predefinito). |
| `FLUXURA_CELERY_RESULT_BACKEND` | Backend dei risultati Celery. |
| `FLUXURA_INVOICE_OUTPUT_DIR` | Directory in cui salvare gli XML. |
| `FLUXURA_XSD_PATH` | XSD alternativo; se vuoto si usa quello incluso nel pacchetto. |

Avvio locale dell'API e del worker:

```bash
uvicorn fluxura.api.app:app
celery -A fluxura.celery_app:celery_app worker -l info
```

La disponibilità dell'API presuppone che sia eseguita separatamente dal
worker e che PostgreSQL/Redis siano raggiungibili secondo la configurazione.

## Test su killercoda o altrove

In un ambiente temporaneo potrebbe essere necessario autenticarsi al registry
Docker prima del deploy:

```bash
docker login
```

Clonare il repository e avviare il deploy usando l'immagine `v1.1.0`:

```bash
git clone https://github.com/murador/fluxura.git
cd fluxura
DOCKER_USERNAME=glutters IMAGE_TAG=v1.1.0 ./scripts/docker/build-and-deploy.sh --deploy-only
```

## 8. Verifica automatizzata

La suite in `tests/` copre la validazione e conversione dei dati in ingresso,
gli endpoint API, la lettura della sorgente SQLAlchemy, la generazione XML e
la validazione XSD, inclusi documenti non validi e DTD. I test verificano
comportamenti dei moduli e non attestano l'integrazione con un provider PEC,
la persistenza dello stato tra worker o un deployment distribuito completo.

## 9. Aspetti operativi e sicurezza da completare

- L'API non implementa autenticazione o autorizzazione.
- L'approvazione manuale è simulata e l'invio PEC è uno stub: non considerarli
  processi effettivi di approvazione o trasmissione fiscale.
- Il repository dello stato è volatile; non è adatto a tracciare il ciclo
  operativo in produzione.
- Gli XML devono essere collocati su storage condiviso e protetto quando i
  worker sono distribuiti.
- Credenziali, segreti e policy di rete devono essere gestiti con strumenti
  specifici dell'ambiente; i valori d'esempio nei manifesti non sono una
  configurazione di produzione.
