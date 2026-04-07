"""Configurazione Celery alternativa in stile file flat.

Utile in deployment dockerizzati dove worker/beat importano direttamente
questo modulo senza passare dalla configurazione applicativa.
"""

# URL del broker usato per accodare i task.
broker_url = "redis://redis:6379/0"
# Backend per persistenza dei risultati dei task.
result_backend = "redis://redis:6379/1"

# Formati di serializzazione consentiti per sicurezza/interoperabilità.
task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]
timezone = "Europe/Rome"
enable_utc = True

# Parametri worker: parallelismo, affidabilità ack e timeout visibilità code.
worker_concurrency = 4
task_acks_late = True
broker_transport_options = {"visibility_timeout": 3600}

# Eventi task/worker utili per monitoraggio (es. Flower).
worker_send_task_events = True
task_send_sent_event = True
