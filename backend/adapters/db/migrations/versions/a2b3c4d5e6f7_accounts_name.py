"""add nullable name column to accounts

Revision ID: a2b3c4d5e6f7
Revises: c1d2e3f4a5b6
Create Date: 2026-08-13

Nullable with no server_default and no backfill on purpose: NULL is a value this
column carries for the life of the row, not a transitional state. "No display
name" is first-class -- `PATCH /api/v1/auth/me` with `""` or `null` puts a row
back here -- so a backfill to `''` would destroy the distinction the read path
reports as `"name": null` and the header renders its email fallback from.

Text rather than String(60): the 60-code-point bound is the domain's
(`AccountName`), and a VARCHAR(n) in Postgres counts characters the same way but
answers an over-length write with a 22001 driver error -- a 500 -- instead of the
documented 400. The bound belongs where it can be refused politely.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("name", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("accounts", "name")
