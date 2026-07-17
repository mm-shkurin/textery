"""track generations.updated_at, so staleness means "stalled", not "old"

The sweep looked for pending/in_progress rows with `created_at < older_than`.
created_at never changes, so requeueing a stale row did not make it fresh: the
row matched again on the very next sweep, and every sweep after that. At a
60-second interval and a 10-minute threshold, one stuck generation triggered a
paid provider call every minute, indefinitely. Confirmed against a real database
before this change -- three consecutive sweeps requeued the same row three times.

updated_at is written on every state transition, so a requeued row is not stale
again until the threshold passes without further progress. That is what the sweep
meant by stale all along.

It is a storage-owned audit column: the domain does not carry it, the same way
Document's updated_at is set by its adapter. Nothing in the domain has to change.

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "d0e1f2a3b4c5"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None

_SWEEP_INDEX = "ix_generations_sweep"


def upgrade() -> None:
    # Backfilled from created_at rather than now(): a row that has genuinely been
    # stalled since before this migration should stay eligible for the sweep.
    # now() would reset every stuck row's clock and hide them for another
    # interval. NOT NULL is set after the backfill so existing rows can be filled
    # first.
    op.add_column(
        "generations",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("UPDATE generations SET updated_at = created_at WHERE updated_at IS NULL")
    op.alter_column("generations", "updated_at", nullable=False)

    # The sweep's exact predicate: status IN (...) AND updated_at < :t. Leading
    # with status keeps the scan off completed/failed rows, which are the bulk of
    # the table and never sweepable. The old status-only index is redundant once
    # this exists -- every query that used it starts with the same column.
    op.create_index(_SWEEP_INDEX, "generations", ["status", "updated_at"])
    op.drop_index("ix_generations_status", table_name="generations")


def downgrade() -> None:
    op.create_index("ix_generations_status", "generations", ["status"])
    op.drop_index(_SWEEP_INDEX, table_name="generations")
    op.drop_column("generations", "updated_at")
