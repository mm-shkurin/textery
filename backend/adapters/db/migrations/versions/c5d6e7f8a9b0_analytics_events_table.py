"""analytics_events table

Revision ID: c5d6e7f8a9b0
Revises: b3c4d5e6f7a8
Create Date: 2026-08-20

The WHOLE table at once, deliberately -- not a column per scenario. The
TDD-minimal split was considered and rejected in
`ProductSpecification/stories/14-analytics-event-tracking/decisions/analytics-ingest-shape-decision.md`:
adding the unique index after the route has served React StrictMode double-fires
aborts on the duplicates already stored, and adding `sequence BIGINT IDENTITY` to
a populated table is a full rewrite holding ACCESS EXCLUSIVE on the product's
busiest write path.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from analytics.event_names import EVENT_NAMES

revision: str = "c5d6e7f8a9b0"
down_revision: Union[str, None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Iterated from the domain catalogue, not written out as twelve literals. Infra
# §1.6 runs `alembic upgrade head` in CI, so a name added to `EVENT_NAMES` without
# a migration goes red here; twelve literals would stay green through that drift.
_EVENT_NAMES_SQL = ", ".join(repr(name) for name in EVENT_NAMES)


def upgrade() -> None:
    op.create_table(
        "analytics_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        # A stable unique SORT key, explicitly NOT a gap-safe tailing cursor: an
        # IDENTITY value is assigned at INSERT and becomes visible at COMMIT, and
        # under concurrency the two orders differ.
        sa.Column("sequence", sa.BigInteger, sa.Identity(always=True), nullable=False),
        sa.Column("event_name", sa.String, nullable=False),
        # Nullable for the rolling-deploy window and for generations already in
        # flight, which carry no visitor (`endpoints.md` §5). The browser route
        # still refuses a request without one.
        sa.Column("visitor_id", UUID(as_uuid=True), nullable=True),
        sa.Column("occurrence_key", UUID(as_uuid=True), nullable=True),
        # SET NULL, not CASCADE and not the repo's usual NO ACTION: analytics rows
        # survive account erasure with the account detached, because Story 15's
        # cohort figures need them.
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # NOT NULL default `{}`: absent, explicit null and `{}` all store `{}`, so
        # Story 15 never reads two spellings of "no context" (`endpoints.md` §1).
        sa.Column("payload", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("degraded", sa.Boolean, nullable=False, server_default=sa.text("false")),
        # `timestamptz` at default precision. TIMESTAMP(0) would truncate every
        # event to the second.
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            f"event_name IN ({_EVENT_NAMES_SQL})",
            name="ck_analytics_events_event_name",
        ),
    )
    # PARTIAL. A plain UNIQUE is NULLS DISTINCT and would be void on the
    # server-emitted rows whose `occurrence_key` is NULL; NULLS NOT DISTINCT fails
    # the other way and collapses every server-emitted event for one visitor into
    # one row. Scoped, it governs client-origin rows only -- and it is what makes
    # `ON CONFLICT (visitor_id, occurrence_key) DO NOTHING` an atomic collapse
    # rather than a read-then-insert race.
    op.create_index(
        "uq_analytics_events_visitor_occurrence",
        "analytics_events",
        ["visitor_id", "occurrence_key"],
        unique=True,
        postgresql_where=sa.text("occurrence_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_analytics_events_visitor_occurrence", table_name="analytics_events")
    op.drop_table("analytics_events")
