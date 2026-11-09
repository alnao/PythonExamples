"""API REST della biblioteca: FastAPI + SQLAlchemy 2.0 + PostgreSQL.

Documentazione interattiva su http://localhost:8000/docs
"""
from typing import Annotated

from fastapi import Depends, FastAPI, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import repository as repo
from .database import get_session
from .schemas import (AutoreConConteggio, AutoreConLibri, AutoreIn, AutoreOut, LibroIn,
                      LibroOut, PrestitoIn, PrestitoOut, Statistiche)

app = FastAPI(title="Biblioteca - SQLAlchemy e PostgreSQL", version="1.0")

SessionDep = Annotated[Session, Depends(get_session)]


# le eccezioni del repository diventano risposte HTTP in un solo punto
@app.exception_handler(repo.NonTrovatoError)
def non_trovato(_: Request, errore: repo.NonTrovatoError):
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(errore)})


@app.exception_handler(repo.OperazioneNonValidaError)
def non_valida(_: Request, errore: repo.OperazioneNonValidaError):
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(errore)})


@app.exception_handler(IntegrityError)
def vincolo_violato(_: Request, errore: IntegrityError):
    # unique, foreign key o check violati: il messaggio originale del database è in errore.orig
    return JSONResponse(status_code=status.HTTP_409_CONFLICT,
                        content={"detail": "Vincolo del database violato", "db": str(errore.orig).splitlines()[0]})


@app.get("/")
def stato(session: SessionDep):
    versione = session.scalar(text("SELECT version()")) if session.bind.dialect.name == "postgresql" else "sqlite"
    return {"stato": "ok", "database": versione}


# ---------- autori ----------

@app.post("/autori", response_model=AutoreOut, status_code=status.HTTP_201_CREATED)
def crea_autore(dati: AutoreIn, session: SessionDep):
    return repo.crea_autore(session, dati.nome, dati.cognome, dati.nato_il)


@app.get("/autori", response_model=list[AutoreConConteggio])
def lista_autori(session: SessionDep):
    return [AutoreConConteggio(**AutoreOut.model_validate(a).model_dump(), numero_libri=n)
            for a, n in repo.lista_autori(session)]


@app.get("/autori/{autore_id}", response_model=AutoreConLibri)
def get_autore(autore_id: int, session: SessionDep):
    return repo.get_autore(session, autore_id)


@app.delete("/autori/{autore_id}", status_code=status.HTTP_204_NO_CONTENT)
def elimina_autore(autore_id: int, session: SessionDep):
    repo.elimina_autore(session, autore_id)


# ---------- libri ----------

@app.post("/libri", response_model=LibroOut, status_code=status.HTTP_201_CREATED)
def crea_libro(dati: LibroIn, session: SessionDep):
    return repo.crea_libro(session, **dati.model_dump())


@app.get("/libri", response_model=list[LibroOut])
def cerca_libri(
    session: SessionDep,
    q: Annotated[str | None, Query(description="testo nel titolo o nel cognome dell'autore")] = None,
    categoria: str | None = None,
    autore_id: int | None = None,
    anno_da: int | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return repo.cerca_libri(session, testo=q, categoria=categoria, autore_id=autore_id,
                            anno_da=anno_da, limit=limit, offset=offset)


@app.get("/libri/{libro_id}", response_model=LibroOut)
def get_libro(libro_id: int, session: SessionDep):
    return repo.get_libro(session, libro_id)


# ---------- prestiti ----------

@app.post("/libri/{libro_id}/prestiti", response_model=PrestitoOut, status_code=status.HTTP_201_CREATED)
def presta(libro_id: int, dati: PrestitoIn, session: SessionDep):
    return repo.presta_libro(session, libro_id, dati.utente)


@app.post("/prestiti/{prestito_id}/restituzione", response_model=PrestitoOut)
def restituisci(prestito_id: int, session: SessionDep):
    return repo.restituisci(session, prestito_id)


@app.get("/statistiche", response_model=Statistiche)
def statistiche(session: SessionDep):
    return repo.statistiche(session)


@app.get("/libri/{libro_id}/disponibili")
def disponibili(libro_id: int, session: SessionDep):
    libro = repo.get_libro(session, libro_id)      # se non esiste solleva NonTrovatoError => 404
    return {"libro_id": libro_id, "copie": libro.copie, "disponibili": repo.copie_disponibili(session, libro)}
