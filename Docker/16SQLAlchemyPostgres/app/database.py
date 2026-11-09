"""Connessione al database: engine (pool di connessioni) e fabbrica delle sessioni."""
import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# postgresql+psycopg = driver psycopg 3; in Docker l'host è il servizio "db"
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://biblioteca:biblioteca@localhost:5433/biblioteca"
)

engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("SQL_ECHO") == "1",   # SQL_ECHO=1 stampa ogni query eseguita
    pool_pre_ping=True,                  # verifica la connessione prima di usarla (db riavviato)
)

# expire_on_commit=False: dopo il commit gli oggetti restano leggibili senza nuove query
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """Dipendenza FastAPI: una sessione per richiesta, chiusa sempre alla fine."""
    with SessionLocal() as session:
        yield session
