# Fluxura

Pipeline distribuita e verificabile per la gestione di alti volumi di fatture elettroniche (FatturaPA).

## Obiettivo

Organizzare il progetto in 5 fasi operative indipendenti e scalabili:

1. **Estrazione**: query su DB e lettura soggetti.
2. **Calcolo**: importi, IVA, sconti e regole fiscali.
3. **Generazione**: XML conforme FatturaPA.
4. **Verifica**: validazione XSD e approvazione manuale.
5. **Invio PEC**: invio tramite API PEC/SMTP/SDI.

## Struttura del progetto

```text
fluxura/
├── src/fluxura/
│   ├── domain/                 # Entità e stati di dominio
│   ├── infrastructure/         # Persistenza e repository
│   ├── services/               # Logica per ogni fase della pipeline
│   ├── pipeline/
│   │   ├── tasks.py            # Task Celery per pipeline distribuita
│   │   └── workflows/
│   │       ├── prefect_flow.py # Orchestrazione con Prefect
│   │       └── airflow_dag.py  # DAG opzionale Airflow
│   ├── celery_app.py           # Istanza Celery principale
│   └── config.py               # Configurazione centralizzata
├── docs/
├── tests/
├── celeryconfig.py
├── docker-compose.yml
└── pyproject.toml
```

## Punti di caricamento (ingestion)

L'API Gateway (`fluxura.api.app`, nessuna autenticazione per ora) accoda la pipeline su Celery:

- `POST /invoices` – fattura in formato JSON (validata con Pydantic, `fluxura.ingestion.schemas.InvoiceIn`).
- `POST /invoices/{invoice_id}/process` – carica la fattura da Postgres (tabelle `invoices` / `invoice_lines`, vedi `fluxura.ingestion.sources`).

Avvio: `uvicorn fluxura.api.app:app`. Programmaticamente: `dispatch_invoice_pipeline(invoice_id=42)` oppure `dispatch_invoice_pipeline(payload={...})`.

## Tecnologie chiave

- **Celery + Redis/RabbitMQ**: esecuzione task asincroni e scalabilità orizzontale.
- **Prefect / Airflow**: orchestrazione a DAG, pause, retry, approvazioni.
- **PostgreSQL**: stato fattura (`estratta`, `calcolata`, `xml_generato`, `verificata`, `inviata`) e logging errori.

## Quick start

```bash
docker-compose up -d
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Avvio worker Celery:

```bash
celery -A fluxura.celery_app:celery_app worker -l info
```

### Popolamento database demo

Per un ambiente temporaneo come Killercoda, dopo l'avvio dei container si puo'
creare lo schema minimo e caricare due fatture inventate:

```bash
docker compose up -d postgres
./scripts/docker/seed_database.sh
```

Lo script e' idempotente e usa il servizio `postgres` del
`docker-compose.yml`. Le fatture demo hanno gli ID `1001` e `1002`; per
verificarle:

```bash
docker compose exec postgres psql -U fluxura -d fluxura \
  -c "SELECT id, numero_fattura FROM invoices ORDER BY id;"
```

Per provare il caricamento dalla sorgente Postgres, configurare l'applicazione
con `FLUXURA_DATABASE_URL=postgresql+psycopg://fluxura:fluxura@localhost:5432/fluxura`
e usare `invoice_id=1001`.

### Troubleshooting: `pkg_resources.VersionConflict` su `vine`

Se all'avvio di Celery compare un errore simile a:

`pkg_resources.VersionConflict: (vine 5.0.0 (...), Requirement.parse('vine<6.0,>=5.1.0'))`

la causa più comune è un **mix tra pacchetti di sistema e pacchetti installati in virtualenv**:

- lo script `/usr/bin/celery` (installato via `apt`) usa `pkg_resources` e cerca dipendenze nei path di sistema;
- la versione di `celery` caricata richiede `vine>=5.1.0`;
- nel path attivo viene trovata `vine==5.0.0` da `/usr/lib/python3/dist-packages`, incompatibile.

Verifiche utili:

```bash
which celery
python -c "import sys; print('\\n'.join(sys.path))"
python -m pip show celery vine
python -m pip check
```

Risoluzione consigliata (isolamento ambiente):

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip setuptools wheel
python -m pip install -e .
python -m celery -A fluxura.celery_app:celery_app worker -l info
```

Note:

- preferire `python -m celery` evita di invocare accidentalmente `/usr/bin/celery`;
- evitare installazioni miste `apt` + `pip` nello stesso interprete Python.

Dispatch pipeline:

```python
from fluxura.pipeline.tasks import dispatch_invoice_pipeline

dispatch_invoice_pipeline(invoice_id=42)
```

## Installazione automatizzata

### Docker

```bash
./scripts/docker/install.sh
```

Script di cleanup:

```bash
./scripts/docker/uninstall.sh
```

### Kubernetes

Prerequisiti: `kubectl` configurato (cluster locale o remoto) e Docker disponibile per build immagine.

```bash
./scripts/k8s/deploy.sh
```

Cleanup ambiente Kubernetes:

```bash
./scripts/k8s/teardown.sh
```
