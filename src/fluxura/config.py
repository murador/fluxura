from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="FLUXURA_")

    app_env: str = "dev"
    database_url: str = "postgresql+psycopg://fluxura:fluxura@localhost:5432/fluxura"

    celery_broker_url: str = Field(default="redis://localhost:6379/0")
    celery_result_backend: str = Field(default="redis://localhost:6379/1")

    invoice_output_dir: str = "artifacts/xml"


settings = Settings()
