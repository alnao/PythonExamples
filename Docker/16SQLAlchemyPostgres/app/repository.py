"""Accesso ai dati: tutte le query SQLAlchemy stanno qui, le API in main.py non scrivono SQL.

Stile 2.0: select(...) costruisce la query, session.scalars()/session.execute() la esegue.
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from .models import Autore, Categoria, Libro, Prestito, libri_categorie


class NonTrovatoError(Exception):
    pass


class OperazioneNonValidaError(Exception):
    pass


# ---------- autori ----------

def crea_autore(session: Session, nome: str, cognome: str, nato_il: date | None = None) -> Autore:
    autore = Autore(nome=nome, cognome=cognome, nato_il=nato_il)
    session.add(autore)
    session.commit()          # IntegrityError se l'autore esiste già (vincolo unique)
    return autore


def lista_autori(session: Session) -> list[tuple[Autore, int]]:
    """Autori con il numero di libri: LEFT OUTER JOIN + GROUP BY, una sola query."""
    query = (
        select(Autore, func.count(Libro.id).label("numero_libri"))
        .outerjoin(Autore.libri)
        .group_by(Autore.id)
        .order_by(Autore.cognome, Autore.nome)
    )
    return [(autore, numero) for autore, numero in session.execute(query)]


def get_autore(session: Session, autore_id: int) -> Autore:
    # selectinload carica i libri con una seconda query "WHERE autore_id IN (...)"
    autore = session.scalar(
        select(Autore).where(Autore.id == autore_id).options(selectinload(Autore.libri))
    )
    if autore is None:
        raise NonTrovatoError(f"Autore {autore_id} non trovato")
    return autore


def elimina_autore(session: Session, autore_id: int) -> None:
    session.delete(get_autore(session, autore_id))   # cascade: elimina anche i libri
    session.commit()


# ---------- categorie e libri ----------

def categorie_per_nome(session: Session, nomi: list[str]) -> list[Categoria]:
    """Restituisce le categorie con quei nomi, creando quelle che mancano."""
    nomi = sorted({n.strip().lower() for n in nomi if n.strip()})
    esistenti = {c.nome: c for c in session.scalars(select(Categoria).where(Categoria.nome.in_(nomi)))}
    nuove = [Categoria(nome=n) for n in nomi if n not in esistenti]
    session.add_all(nuove)
    return [*esistenti.values(), *nuove]


def crea_libro(session: Session, *, titolo: str, isbn: str, anno: int, prezzo: Decimal,
               autore_id: int, copie: int = 1, categorie: list[str] | None = None) -> Libro:
    autore = session.get(Autore, autore_id)          # get = lettura per chiave primaria
    if autore is None:
        raise NonTrovatoError(f"Autore {autore_id} non trovato")
    libro = Libro(titolo=titolo, isbn=isbn, anno=anno, prezzo=prezzo, copie=copie, autore=autore,
                  categorie=categorie_per_nome(session, categorie or []))
    session.add(libro)
    session.commit()
    return get_libro(session, libro.id)


def _query_libri():
    # carica autore e categorie insieme ai libri: evita il problema "N+1 query"
    return select(Libro).options(selectinload(Libro.autore), selectinload(Libro.categorie))


def get_libro(session: Session, libro_id: int) -> Libro:
    libro = session.scalar(_query_libri().where(Libro.id == libro_id))
    if libro is None:
        raise NonTrovatoError(f"Libro {libro_id} non trovato")
    return libro


def cerca_libri(session: Session, *, testo: str | None = None, categoria: str | None = None,
                autore_id: int | None = None, anno_da: int | None = None,
                limit: int = 20, offset: int = 0) -> list[Libro]:
    """Filtri opzionali aggiunti alla query solo se valorizzati."""
    query = _query_libri()
    if testo:
        modello = f"%{testo}%"
        query = query.join(Libro.autore).where(or_(
            Libro.titolo.ilike(modello), Autore.cognome.ilike(modello)))
    if categoria:
        query = query.where(Libro.categorie.any(Categoria.nome == categoria.lower()))
    if autore_id is not None:
        query = query.where(Libro.autore_id == autore_id)
    if anno_da is not None:
        query = query.where(Libro.anno >= anno_da)
    query = query.order_by(Libro.titolo).limit(limit).offset(offset)
    return list(session.scalars(query))


# ---------- prestiti ----------

def copie_disponibili(session: Session, libro: Libro) -> int:
    aperti = session.scalar(
        select(func.count()).select_from(Prestito)
        .where(Prestito.libro_id == libro.id, Prestito.restituito_il.is_(None))
    )
    return libro.copie - aperti


def presta_libro(session: Session, libro_id: int, utente: str) -> Prestito:
    # with_for_update => SELECT ... FOR UPDATE: blocca la riga del libro fino al commit,
    # così due prestiti contemporanei non possono prendere l'ultima copia (in SQLite viene ignorato)
    libro = session.scalar(select(Libro).where(Libro.id == libro_id).with_for_update())
    if libro is None:
        raise NonTrovatoError(f"Libro {libro_id} non trovato")
    if copie_disponibili(session, libro) <= 0:
        session.rollback()
        raise OperazioneNonValidaError(f"Nessuna copia disponibile di '{libro.titolo}'")
    prestito = Prestito(libro=libro, utente=utente, preso_il=date.today())
    session.add(prestito)
    session.commit()
    return prestito


def restituisci(session: Session, prestito_id: int) -> Prestito:
    prestito = session.get(Prestito, prestito_id)
    if prestito is None:
        raise NonTrovatoError(f"Prestito {prestito_id} non trovato")
    if prestito.restituito_il is not None:
        raise OperazioneNonValidaError("Prestito già restituito")
    prestito.restituito_il = date.today()     # l'ORM rileva la modifica e fa UPDATE al commit
    session.commit()
    return prestito


# ---------- statistiche: query di aggregazione ----------

def statistiche(session: Session) -> dict:
    per_categoria = session.execute(
        select(Categoria.nome, func.count(libri_categorie.c.libro_id))
        .join(libri_categorie, libri_categorie.c.categoria_id == Categoria.id)
        .group_by(Categoria.nome)
        .order_by(func.count(libri_categorie.c.libro_id).desc(), Categoria.nome)
    ).all()
    prolifico = session.execute(
        select(Autore.nome, Autore.cognome, func.count(Libro.id).label("n"))
        .join(Autore.libri)
        .group_by(Autore.id)
        .order_by(func.count(Libro.id).desc(), Autore.cognome)
        .limit(1)
    ).first()
    return {
        "libri": session.scalar(select(func.count()).select_from(Libro)),
        "autori": session.scalar(select(func.count()).select_from(Autore)),
        "prestiti_aperti": session.scalar(
            select(func.count()).select_from(Prestito).where(Prestito.restituito_il.is_(None))),
        "libri_per_categoria": dict(per_categoria),
        "valore_catalogo": session.scalar(select(func.coalesce(func.sum(Libro.prezzo * Libro.copie), 0))),
        "autore_piu_prolifico": f"{prolifico.nome} {prolifico.cognome}" if prolifico else None,
    }
