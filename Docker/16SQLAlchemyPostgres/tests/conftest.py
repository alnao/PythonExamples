"""Fixture dei test: database pulito per ogni test e client HTTP con la sessione sostituita.

Di default i test usano SQLite in memoria (nessun Docker necessario).
Con TEST_DATABASE_URL girano sul PostgreSQL vero, per esempio quello del docker-compose:
    TEST_DATABASE_URL=postgresql+psycopg://biblioteca:biblioteca@localhost:5433/biblioteca pytest
ATTENZIONE: su PostgreSQL ogni test cancella e ricrea le tabelle di quel database.
"""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_session
from app.main import app
from app.models import Base

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite://")


@pytest.fixture(scope="session")
def engine():
    if TEST_DATABASE_URL.startswith("sqlite"):
        # StaticPool: una sola connessione condivisa, altrimenti ogni connessione
        # vedrebbe un database in memoria diverso (e vuoto)
        motore = create_engine(TEST_DATABASE_URL, poolclass=StaticPool,
                               connect_args={"check_same_thread": False})

        @event.listens_for(motore, "connect")
        def attiva_foreign_key(connessione, _record):
            # SQLite ignora le chiavi esterne se non lo si chiede esplicitamente
            connessione.execute("PRAGMA foreign_keys=ON")
    else:
        motore = create_engine(TEST_DATABASE_URL)
    yield motore
    motore.dispose()


@pytest.fixture
def session(engine):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    fabbrica = sessionmaker(engine, expire_on_commit=False)
    with fabbrica() as sessione:
        yield sessione


@pytest.fixture
def client(session):
    # dependency override: le API usano la sessione del test invece di quella vera
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def calvino(client) -> dict:
    risposta = client.post("/autori", json={"nome": "Italo", "cognome": "Calvino", "nato_il": "1923-10-15"})
    assert risposta.status_code == 201
    return risposta.json()


@pytest.fixture
def crea_libro(client, calvino):
    contatore = iter(range(1000))

    def _crea(**campi):
        dati = {"titolo": "Il barone rampante", "isbn": f"978880466{next(contatore):04d}",
                "anno": 1957, "prezzo": "12.00", "copie": 1, "autore_id": calvino["id"],
                "categorie": ["romanzo"]} | campi
        risposta = client.post("/libri", json=dati)
        assert risposta.status_code == 201, risposta.text
        return risposta.json()
    return _crea
