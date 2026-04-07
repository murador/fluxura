"""Inizializzazione dell'app Celery condivisa da producer e worker."""

from celery import Celery

from fluxura.config import settings

# Crea l'istanza Celery usando broker/backend definiti in configurazione.
celery_app = Celery(
    "fluxura",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Parametri di serializzazione e timezone per coerenza tra ambienti.
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Rome",
    enable_utc=True,
)

# Permette a Celery di registrare automaticamente i task nel package pipeline.
celery_app.autodiscover_tasks(["fluxura.pipeline"])
