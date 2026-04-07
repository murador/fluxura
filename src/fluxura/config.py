"""Configurazione centralizzata dell'applicazione Fluxura.

Questo modulo usa Pydantic Settings per leggere variabili d'ambiente con
prefisso ``FLUXURA_`` e fornire valori di default adatti allo sviluppo
locale.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Mappa le impostazioni runtime provenienti da environment/.env.

    Ogni attributo corrisponde a una variabile d'ambiente; se non presente,
    viene usato il default specificato qui.
    """

    # Carica automaticamente il file .env e applica il prefisso FLUXURA_.
    model_config = SettingsConfigDict(env_file=".env", env_prefix="FLUXURA_")

    # Ambiente applicativo (es. dev, staging, prod).
    app_env: str = "dev"
    # DSN SQLAlchemy verso il database principale.
    database_url: str = "postgresql+psycopg://fluxura:fluxura@localhost:5432/fluxura"

    # Endpoint Redis (o altro broker) usato da Celery per mettere i task in coda.
    celery_broker_url: str = Field(default="redis://localhost:6379/0")
    # Backend risultati Celery, dove vengono salvati stati/ritorni dei task.
    celery_result_backend: str = Field(default="redis://localhost:6379/1")

    # Directory destinazione dove salvare gli XML FatturaPA generati.
    invoice_output_dir: str = "artifacts/xml"


# Istanza singleton importabile dal resto del progetto.
settings = Settings()
