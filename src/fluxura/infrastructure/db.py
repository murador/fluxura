"""Bootstrap dell'accesso database con SQLAlchemy."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from fluxura.config import settings

# Engine condiviso con ``pool_pre_ping`` per verificare connessioni stale.
engine = create_engine(settings.database_url, pool_pre_ping=True)

# Factory di sessioni usata dai repository reali (qui placeholder).
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
