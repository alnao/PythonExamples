"""schema iniziale: autori, categorie, libri e associazione libri-categorie

Revision ID: 0001
Revises:
Create Date: 2026-11-09
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "autori",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(100), nullable=False),
        sa.Column("cognome", sa.String(100), nullable=False),
        sa.Column("nato_il", sa.Date(), nullable=True),
        sa.UniqueConstraint("nome", "cognome", name="uq_autori_nome_cognome"),
    )
    op.create_table(
        "categorie",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(50), nullable=False, unique=True),
    )
    op.create_table(
        "libri",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("titolo", sa.String(200), nullable=False),
        sa.Column("isbn", sa.String(13), nullable=False, unique=True),
        sa.Column("anno", sa.Integer(), nullable=False),
        sa.Column("copie", sa.Integer(), nullable=False),
        sa.Column("prezzo", sa.Numeric(8, 2), nullable=False),
        sa.Column("autore_id", sa.Integer(), sa.ForeignKey("autori.id", ondelete="CASCADE"), nullable=False),
        sa.Column("creato_il", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("copie >= 0", name="ck_libri_copie_non_negative"),
        sa.CheckConstraint("prezzo > 0", name="ck_libri_prezzo_positivo"),
    )
    op.create_index("ix_libri_titolo", "libri", ["titolo"])
    op.create_index("ix_libri_autore_id", "libri", ["autore_id"])
    op.create_table(
        "libri_categorie",
        sa.Column("libro_id", sa.Integer(), sa.ForeignKey("libri.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("categoria_id", sa.Integer(), sa.ForeignKey("categorie.id", ondelete="CASCADE"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("libri_categorie")
    op.drop_index("ix_libri_autore_id", table_name="libri")
    op.drop_index("ix_libri_titolo", table_name="libri")
    op.drop_table("libri")
    op.drop_table("categorie")
    op.drop_table("autori")
