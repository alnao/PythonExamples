"""Schemi Pydantic: validano l'input delle API e definiscono la forma delle risposte.

Sono separati dai modelli ORM: l'API non espone per forza tutte le colonne
e la struttura delle tabelle può cambiare senza rompere i client.
"""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class Schema(BaseModel):
    # from_attributes: permette di costruire lo schema da un oggetto ORM (Libro, Autore, ...)
    model_config = ConfigDict(from_attributes=True)


class AutoreIn(Schema):
    nome: str = Field(min_length=1, max_length=100)
    cognome: str = Field(min_length=1, max_length=100)
    nato_il: date | None = None


class AutoreOut(AutoreIn):
    id: int


class AutoreConConteggio(AutoreOut):
    numero_libri: int


class CategoriaOut(Schema):
    id: int
    nome: str


class LibroIn(Schema):
    titolo: str = Field(min_length=1, max_length=200)
    isbn: str = Field(pattern=r"^\d{13}$", description="ISBN-13, solo cifre")
    anno: int = Field(ge=1450, le=2100)
    copie: int = Field(default=1, ge=0)
    prezzo: Decimal = Field(gt=0, max_digits=8, decimal_places=2)
    autore_id: int
    categorie: list[str] = Field(default_factory=list, description="nomi; quelle nuove vengono create")


class LibroOut(Schema):
    id: int
    titolo: str
    isbn: str
    anno: int
    copie: int
    prezzo: Decimal
    autore: AutoreOut
    categorie: list[CategoriaOut]


class LibroBreve(Schema):
    id: int
    titolo: str
    anno: int


class AutoreConLibri(AutoreOut):
    libri: list[LibroBreve]


class PrestitoIn(Schema):
    utente: str = Field(min_length=1, max_length=100)


class PrestitoOut(Schema):
    id: int
    libro_id: int
    utente: str
    preso_il: date
    restituito_il: date | None


class Statistiche(Schema):
    libri: int
    autori: int
    prestiti_aperti: int
    libri_per_categoria: dict[str, int]
    valore_catalogo: Decimal
    autore_piu_prolifico: str | None
