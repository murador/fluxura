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

## Tecnologie chiave

- **Celery + Redis/RabbitMQ**: esecuzione task asincroni e scalabilità orizzontale.
- **Prefect / Airflow**: orchestrazione a DAG, pause, retry, approvazioni.
- **PostgreSQL**: stato fattura (`estratta`, `calcolata`, `xml_generato`, `verificata`, `inviata`) e logging errori.

## Quick start

```bash
docker compose up -d
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Avvio worker Celery:

```bash
celery -A fluxura.celery_app:celery_app worker -l info
```

Dispatch pipeline:

```python
from fluxura.pipeline.tasks import dispatch_invoice_pipeline

dispatch_invoice_pipeline(invoice_id=42)
```
