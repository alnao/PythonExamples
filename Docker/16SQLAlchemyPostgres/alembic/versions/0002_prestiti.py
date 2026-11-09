"""prestiti: tabella aggiunta in un secondo momento, per mostrare l'evoluzione dello schema

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-09
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "prestiti",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("libro_id", sa.Integer(), sa.ForeignKey("libri.id", ondelete="CASCADE"), nullable=False),
        sa.Column("utente", sa.String(100), nullable=False),
        sa.Column("preso_il", sa.Date(), server_default=sa.func.current_date(), nullable=False),
        sa.Column("restituito_il", sa.Date(), nullable=True),
    )
    op.create_index("ix_prestiti_libro_id", "prestiti", ["libro_id"])


def downgrade() -> None:
    op.drop_index("ix_prestiti_libro_id", table_name="prestiti")
    op.drop_table("prestiti")
