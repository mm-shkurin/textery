"""add nullable page_settings column to documents

Revision ID: e7f8a9b0c1d2
Revises: b4c5d6e7f8a9
Create Date: 2026-08-03

Purely additive. The column is NULLABLE and carries no server default, and no
existing row is touched: SQL NULL is the only way a never-configured document
can say so, and a default would spend that vocabulary on every legacy row at
once. See ProductSpecification/stories/10-editor-pages/decisions/
page-settings-read-tristate-decision.md.

The downgrade drops configured settings and is therefore forward-only in
practice.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "e7f8a9b0c1d2"
down_revision: Union[str, None] = "b4c5d6e7f8a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("page_settings", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("documents", "page_settings")
