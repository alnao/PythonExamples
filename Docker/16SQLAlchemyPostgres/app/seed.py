"""Inserisce dati di esempio se il database è vuoto.  Uso:  python -m app.seed"""
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select

from . import repository as repo
from .database import SessionLocal
from .models import Autore

AUTORI = [
    ("Italo", "Calvino", date(1923, 10, 15), [
        ("Il barone rampante", "9788804668237", 1957, "12.00", 3, ["romanzo", "classici"]),
        ("Le città invisibili", "9788804668244", 1972, "11.50", 2, ["romanzo", "classici"]),
        ("Lezioni americane", "9788804668251", 1988, "10.00", 1, ["saggio"]),
    ]),
    ("Primo", "Levi", date(1919, 7, 31), [
        ("Se questo è un uomo", "9788806219352", 1947, "11.00", 4, ["memorie", "classici"]),
        ("Il sistema periodico", "9788806219369", 1975, "12.50", 1, ["racconti"]),
    ]),
    ("Natalia", "Ginzburg", date(1916, 7, 14), [
        ("Lessico famigliare", "9788806219376", 1963, "13.00", 2, ["romanzo", "memorie"]),
    ]),
    ("Umberto", "Eco", date(1932, 1, 5), [
        ("Il nome della rosa", "9788845292613", 1980, "15.00", 2, ["romanzo", "giallo"]),
    ]),
]


def main() -> None:
    with SessionLocal() as session:
        if session.scalar(select(func.count()).select_from(Autore)):
            print("Database già popolato: seed saltato")
            return
        for nome, cognome, nato_il, libri in AUTORI:
            autore = repo.crea_autore(session, nome, cognome, nato_il)
            for titolo, isbn, anno, prezzo, copie, categorie in libri:
                repo.crea_libro(session, titolo=titolo, isbn=isbn, anno=anno, prezzo=Decimal(prezzo),
                                copie=copie, autore_id=autore.id, categorie=categorie)
        repo.presta_libro(session, 1, "alberto")
        print(f"Inseriti {len(AUTORI)} autori e i loro libri")


if __name__ == "__main__":
    main()
