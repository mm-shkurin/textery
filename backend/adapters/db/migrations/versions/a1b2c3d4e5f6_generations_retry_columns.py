"""add idempotency_key and source_generation_id to generations

Revision ID: a1b2c3d4e5f6
Revises: e7f8a9b0c1d2
Create Date: 2026-08-06

Additive, and shaped around the fact that this table is NOT empty and is written
continuously by the stale sweep in every replica -- unlike the `documents`
migration it mirrors, which created its table.

`idempotency_key` is NULLABLE. NOT NULL would abort the deploy on every existing
row, and a backfilled '' would collide on the first account that owns two
generations. Legacy rows keep NULL, and Postgres treats NULLs as distinct, so
they neither collide with each other nor are constrained. New rows carry a key
because the retry endpoint requires the header.

`source_generation_id` is the lineage a retry needs: without it the replay path
cannot tell a repeat of THIS retry from the same key used against a different
source, and the contract's 409 for a reused key would be unwritable.

The unique index is built CONCURRENTLY, outside the migration's transaction. A
plain build takes ACCESS EXCLUSIVE over the whole table while every replica's
sweep is issuing UPDATEs against it.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "e7f8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_UNIQUE_INDEX = "uq_generations_owner_idempotency_key"
_SOURCE_INDEX = "ix_generations_source_generation_id"


def upgrade() -> None:
    op.add_column("generations", sa.Column("idempotency_key", sa.String(length=128), nullable=True))
    op.add_column(
        "generations",
        sa.Column(
            "source_generation_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("generations.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    # CONCURRENTLY cannot run inside a transaction block, and Alembic wraps each
    # migration in one -- so the connection is taken out of it for these two
    # statements. The autocommit block is the reason this migration cannot be
    # merged into a larger one later.
    with op.get_context().autocommit_block():
        op.create_index(
            _UNIQUE_INDEX,
            "generations",
            ["owner_id", "idempotency_key"],
            unique=True,
            postgresql_concurrently=True,
        )
        op.create_index(
            _SOURCE_INDEX,
            "generations",
            ["source_generation_id"],
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.drop_index(_SOURCE_INDEX, table_name="generations", postgresql_concurrently=True)
        op.drop_index(_UNIQUE_INDEX, table_name="generations", postgresql_concurrently=True)
    op.drop_column("generations", "source_generation_id")
    op.drop_column("generations", "idempotency_key")
