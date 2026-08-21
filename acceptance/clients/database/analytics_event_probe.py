"""A read-only probe over `analytics_events`, for the claims HTTP cannot answer.

Story 14 ships no read surface on purpose — `endpoints.md`: "One new endpoint, not a
resource. No `GET /analytics/events`, no aggregate, no export — reading is Story 15".
So "the event is recorded" and "the stored event has no account attached" are only
observable in the database, and `01_API_Tests.md`'s DSL Technical Reference spells the
second one out as exactly that: `analytics_events.user_id IS NULL`.

This keeps the acceptance module's black-box contract. Nothing here imports a backend
module — there is no compile dependency on backend internals; it speaks SQL to the same
Postgres the running application writes to, from a different process.

Every read opens its OWN connection and closes it, which is what «a fresh read» asks
for: `create_session_factory` sets `expire_on_commit=False`, so a re-read inside the
writing session is served from SQLAlchemy's identity map and would pass on a row
Postgres never received. A connection opened here has no identity map to be served
from and no transaction of the writer's to see through.
"""

import os
import uuid
from dataclasses import dataclass
from typing import Optional

import asyncpg

DATABASE_URL_ENV_VAR = "DATABASE_URL"

# Scoped to ONE visitor, and to nothing narrower. The visitor is minted fresh per
# report, so every row this returns was written by the call under test — which makes
# the row COUNT an assertable claim ("exactly one event exists for this visitor")
# rather than a claim about the subset that already matched what was expected.
#
# `occurrence_key` is therefore selected back instead of being pinned in the WHERE:
# a lookup keyed on it can only ever return rows that already carry the right value,
# so a server that stored the event under a rewritten, truncated or NULL key would
# return zero rows and read as "nothing was written at all". Selected, it is compared
# against what was sent, and a wrong key says so.
#
# `visitor_id` is the lookup and so is NOT selected back — reading it would re-assert
# what the WHERE already pinned. Columns are named, never `*`: a probe that selected
# everything would keep passing after a column it reads was renamed.
_SELECT_EVENTS_FOR_VISITOR = (
    "SELECT occurrence_key, event_name, user_id "
    "FROM analytics_events "
    "WHERE visitor_id = $1"
)


@dataclass(frozen=True)
class StoredAnalyticsEvent:
    """One `analytics_events` row, as the database holds it.

    Every column is typed Optional where the database may hold NULL — the dataclass
    reports what was read and coerces nothing, so a NULL that should have been a value
    reaches the assertion as `None` and fails there, loudly, instead of being filled in
    with a default here.
    """

    occurrence_key: Optional[uuid.UUID]
    event_name: Optional[str]
    # NULL is the whole point of scenario 1.1: an anonymous event carries no account.
    user_id: Optional[uuid.UUID]


async def read_events_for(
    visitor_id: uuid.UUID,
) -> tuple[StoredAnalyticsEvent, ...]:
    """Every stored event for one visitor, on a connection of this probe's own."""
    connection = await asyncpg.connect(_dsn())
    try:
        rows = await connection.fetch(_SELECT_EVENTS_FOR_VISITOR, visitor_id)
    finally:
        await connection.close()
    return tuple(
        StoredAnalyticsEvent(
            occurrence_key=row["occurrence_key"],
            event_name=row["event_name"],
            user_id=row["user_id"],
        )
        for row in rows
    )


def _dsn() -> str:
    """The same connection string the application under test was booted with.

    Asserted rather than defaulted, on the same contract `conftest.py` applies to the
    OAuth handoff TTL: a probe that silently fell back to a localhost default could
    read a DIFFERENT database from the one the backend writes to and report "nothing
    was stored" about a row that exists.
    """
    database_url = os.environ.get(DATABASE_URL_ENV_VAR, "")
    assert database_url, (
        f"the stored-row assertions need {DATABASE_URL_ENV_VAR} set to the same "
        "connection string the backend under test was booted with, e.g. "
        "postgresql://user:password@localhost:5432/db"
    )
    # The application accepts the SQLAlchemy dialect spelling (`session.py`'s
    # `to_async_database_url`); asyncpg's own connect() does not.
    return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
