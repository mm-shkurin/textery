import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from analytics.event_names import EVENT_NAMES
from model.base import Base

# Built by ITERATING the domain catalogue, never written out as twelve literals.
# Same approach as ck_documents_document_type and ck_generations_status, and here
# it is load-bearing: Infra §1.6 runs `alembic upgrade head` against the test
# database in CI, so a thirteenth name added to `EVENT_NAMES` without a migration
# goes red. Twelve literals would stay green through that drift forever.
_EVENT_NAMES_SQL = ", ".join(repr(name) for name in EVENT_NAMES)


class AnalyticsEventModel(Base):
    """One row of `analytics_events`.

    The whole table lands in one migration rather than growing a column per
    scenario (`decisions/analytics-ingest-shape-decision.md`): adding the unique
    index after the route has served React StrictMode double-fires aborts on the
    duplicates already stored, and adding an IDENTITY column to a populated table
    rewrites it under ACCESS EXCLUSIVE on the product's busiest write path.
    """

    __tablename__ = "analytics_events"
    __table_args__ = (
        CheckConstraint(
            f"event_name IN ({_EVENT_NAMES_SQL})",
            name="ck_analytics_events_event_name",
        ),
        # PARTIAL, and that is the whole point. A plain UNIQUE is `NULLS DISTINCT`
        # in Postgres, so it would be void on exactly the server-emitted rows whose
        # `occurrence_key` is NULL; `NULLS NOT DISTINCT` fails the other way and
        # collapses every server-emitted event for one visitor into a single row.
        # Scoped `WHERE occurrence_key IS NOT NULL`, the constraint governs
        # client-origin rows only, and server-emitted dedupe stays a separate
        # mechanism for the scenario that introduces it.
        Index(
            "uq_analytics_events_visitor_occurrence",
            "visitor_id",
            "occurrence_key",
            unique=True,
            postgresql_where=text("occurrence_key IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    # A stable, unique SORT key -- and nothing more. It is NOT a gap-safe tailing
    # cursor: an IDENTITY value is assigned at INSERT and becomes visible at
    # COMMIT, and under concurrency those two orders differ, so a reader tailing
    # `sequence > last_seen` permanently skips rows whose transaction committed
    # late. Story 15 reads this design as its warrant; the contract is written here
    # so it cannot read a promise this column does not make.
    sequence: Mapped[int] = mapped_column(BigInteger, Identity(always=True), nullable=False)
    event_name: Mapped[str] = mapped_column(String, nullable=False)
    # Nullable: every generation in flight when this migration lands, and every one
    # created by an N-1 replica during the rolling window, has no visitor. A
    # sentinel visitor would pollute every unique-visitor count with one enormous
    # fake browser, and omitting the event would lose a real completion silently
    # (`endpoints.md` §5). The browser route still requires one.
    visitor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # NULL on server-emitted rows, which have no client-minted key to collapse on.
    occurrence_key: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # SET NULL, a deliberate departure from this repo's `NO ACTION`-plus-ordered-
    # delete convention for `accounts` children. Analytics rows SURVIVE account
    # erasure with the account detached, because Story 15's cohort figures need
    # them; `SqlAlchemyAccountEraser`'s docstring records the departure.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    # NOT NULL with a `{}` default: absent, explicit null and `{}` all store `{}`,
    # so Story 15 never has two spellings of "no context" to handle at every read
    # (`endpoints.md` §1).
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    # Its own column, not a `payload` key: `payload` is free-form, capped and
    # stored verbatim for Story 15, and a marker that governs whether a row counts
    # toward unique visitors cannot live inside the blob it qualifies.
    degraded: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    # `timezone=True` maps to `timestamptz`, whose default precision keeps
    # microseconds. A `TIMESTAMP(0)` column would truncate every event to the
    # second, which the storage test pins with a non-zero sub-second instant.
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
