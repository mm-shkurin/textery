"""add avatar columns to accounts

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-08-14

Three nullable columns, and they are NULL or set together -- there is no state
where bytes exist without their media type. Nullable rather than a side table
because "no avatar" is the common case and an outer join on the product's
highest-rate read buys nothing over three NULLs.

In Postgres, `bytea` over ~2 KB is TOASTed out of line and compressed, so the
main heap row stays small and a SELECT that does not name `avatar_bytes` never
touches the TOAST table. That is a storage-level backstop, NOT the guard: the
column is also mapped `deferred=True` and no read path names it except the one
that serves the image. See AccountModel.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, None] = "a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("avatar_bytes", sa.LargeBinary(), nullable=True))
    op.add_column("accounts", sa.Column("avatar_media_type", sa.Text(), nullable=True))
    op.add_column(
        "accounts",
        sa.Column("avatar_updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("accounts", "avatar_updated_at")
    op.drop_column("accounts", "avatar_media_type")
    op.drop_column("accounts", "avatar_bytes")
