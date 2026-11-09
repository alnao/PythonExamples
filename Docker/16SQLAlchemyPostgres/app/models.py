"""Modelli ORM in stile SQLAlchemy 2.0: classi Python tipizzate mappate sulle tabelle.

Relazioni:
- Autore 1 --- N Libro         (chiave esterna libri.autore_id)
- Libro  N --- N Categoria     (tabella di associazione libri_categorie)
- Libro  1 --- N Prestito      (tabella aggiunta dalla seconda migrazione Alembic)
"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (CheckConstraint, Column, ForeignKey, Numeric, String, Table,
                        UniqueConstraint, func)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# tabella di associazione pura (senza colonne proprie): non serve una classe
libri_categorie = Table(
    "libri_categorie",
    Base.metadata,
    Column("libro_id", ForeignKey("libri.id", ondelete="CASCADE"), primary_key=True),
    Column("categoria_id", ForeignKey("categorie.id", ondelete="CASCADE"), primary_key=True),
)


class Autore(Base):
    __tablename__ = "autori"
    __table_args__ = (UniqueConstraint("nome", "cognome", name="uq_autori_nome_cognome"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100))
    cognome: Mapped[str] = mapped_column(String(100))
    nato_il: Mapped[date | None]            # Optional => colonna nullable

    # cascade delete-orphan: cancellando l'autore si cancellano anche i suoi libri
    libri: Mapped[list["Libro"]] = relationship(
        back_populates="autore", cascade="all, delete-orphan", order_by="Libro.anno"
    )

    def __repr__(self) -> str:
        return f"Autore({self.id}, {self.nome} {self.cognome})"


class Categoria(Base):
    __tablename__ = "categorie"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(50), unique=True)

    libri: Mapped[list["Libro"]] = relationship(secondary=libri_categorie, back_populates="categorie")


class Libro(Base):
    __tablename__ = "libri"
    __table_args__ = (
        CheckConstraint("copie >= 0", name="ck_libri_copie_non_negative"),
        CheckConstraint("prezzo > 0", name="ck_libri_prezzo_positivo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    titolo: Mapped[str] = mapped_column(String(200), index=True)
    isbn: Mapped[str] = mapped_column(String(13), unique=True)
    anno: Mapped[int]
    copie: Mapped[int] = mapped_column(default=1)
    prezzo: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    autore_id: Mapped[int] = mapped_column(ForeignKey("autori.id", ondelete="CASCADE"), index=True)
    creato_il: Mapped[datetime] = mapped_column(server_default=func.now())

    autore: Mapped[Autore] = relationship(back_populates="libri")
    categorie: Mapped[list[Categoria]] = relationship(
        secondary=libri_categorie, back_populates="libri", order_by="Categoria.nome"
    )
    prestiti: Mapped[list["Prestito"]] = relationship(back_populates="libro", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"Libro({self.id}, {self.titolo!r})"


class Prestito(Base):
    __tablename__ = "prestiti"

    id: Mapped[int] = mapped_column(primary_key=True)
    libro_id: Mapped[int] = mapped_column(ForeignKey("libri.id", ondelete="CASCADE"), index=True)
    utente: Mapped[str] = mapped_column(String(100))
    preso_il: Mapped[date] = mapped_column(server_default=func.current_date())
    restituito_il: Mapped[date | None]

    libro: Mapped[Libro] = relationship(back_populates="prestiti")
