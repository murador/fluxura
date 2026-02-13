# Architettura pipeline distribuita

## Fasi

| Fase | Modulo | Output |
| --- | --- | --- |
| Estrazione | `services/extraction.py` | `InvoicePayload` |
| Calcolo | `services/calculation.py` | Totali (imponibile, IVA, totale) |
| Generazione XML | `services/xml_generation.py` | file XML FatturaPA |
| Verifica | `services/verification.py` | esito validazione + approvazione |
| Invio PEC | `services/pec_sender.py` | esito invio |

## Tracciamento stato

Lo stato viene aggiornato dal repository con enum `InvoiceStatus`:

- `estratta`
- `calcolata`
- `xml_generato`
- `verificata`
- `inviata`
- `errore`

## Orchestrazione

- Pipeline asincrona distribuita: `pipeline/tasks.py` (Celery chain).
- Workflow declarativo: `pipeline/workflows/prefect_flow.py`.
- Alternativa enterprise: `pipeline/workflows/airflow_dag.py`.
