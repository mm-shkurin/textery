"""add nullable title column to documents

Revision ID: a3b4c5d6e7f8
Revises: 1a2b3c4d5e6f
Create Date: 2026-07-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a3b4c5d6e7f8"
down_revision: Union[str, None] = "1a2b3c4d5e6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("title", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("documents", "title")
