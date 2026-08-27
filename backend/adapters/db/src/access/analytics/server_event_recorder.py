"""The fail-open recorder the product's own routes emit through.

Three properties, each of which is the reason one scenario passes:

* **Its own session.** Built from the session factory per call, never handed the
  caller's. A failed INSERT poisons the transaction it ran in, so sharing the
  product's session would turn "analytics failed" into "the registration rolled
  back" (§12.1, §12.4).
* **It swallows everything, and logs.** A recorder that cannot record must change
  no product outcome -- but silence is its own failure mode, so every swallow
  leaves one structured line naming the event and the error class (§12.2). The
  line carries no payload and no identifier: it is written on paths that handle
  credentials, and a log is not a place to widen who can read them.
* **It is bounded in time.** A dependency that hangs is worse than one that
  fails, because a caller waiting on it holds a request open (§12.3). The wait is
  capped and a timeout is just another swallowed failure.

It executes `insert_of` — the statement builder its sibling store also uses —
rather than calling `SqlAlchemyAnalyticsEventRepository`. One third-layer adapter
must not call another (`.claude/rules/coding-rules.md`); a module-level statement
builder is shared code, not a peer. Nothing is lost by not going through the
repository: that class exists to INTERPRET a refused insert into a `SaveOutcome`,
and a fail-open recorder has no use for the answer — a conflict here means the
transition was already reported, which is success.

`occurrence_key` is a DERIVED key when the emitter has a natural subject to derive
one from (`uuid5` of the transition being reported), and NULL otherwise. Where it
is present the partial unique index performs the collapse itself, so a completion
reported twice from two instances stores one row (§9.3) without a read-then-insert
that would race.
"""

import asyncio
import logging
from collections.abc import Callable
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from access.analytics.analytics_event_storage import insert_of
from analytics.analytics_event import AnalyticsEvent
from shared.clock import Clock

logger = logging.getLogger(__name__)

# Seconds. Generous against a healthy Postgres (this is one INSERT with no
# contention) and short against a caller's own deadline, which is what the bound
# is chosen relative to: every hop on one request has to fit inside it (§12.8).
RECORDING_TIMEOUT_SECONDS = 2.0


class SqlAlchemyServerEventRecorder:
    """`AnalyticsRecorder` over Postgres. Never raises. See the module docstring."""

    def __init__(
        self,
        session_factory: Callable[[], AsyncSession],
        clock: Clock,
        timeout_seconds: float = RECORDING_TIMEOUT_SECONDS,
    ) -> None:
        self._session_factory = session_factory
        self._clock = clock
        self._timeout_seconds = timeout_seconds

    async def record(
        self,
        event_name: str,
        visitor_id: UUID | None,
        user_id: UUID | None,
        payload: dict[str, Any] | None = None,
        occurrence_key: UUID | None = None,
    ) -> None:
        try:
            await asyncio.wait_for(
                self._insert(event_name, visitor_id, user_id, payload, occurrence_key),
                timeout=self._timeout_seconds,
            )
        except Exception as error:
            # Broad on purpose, and the one place in this codebase where that is
            # the point rather than a compromise: the caller is mid-registration
            # or mid-generation, and NOTHING analytics does may reach it.
            logger.warning(
                "analytics event %s was not recorded: %s", event_name, type(error).__name__
            )

    async def _insert(
        self,
        event_name: str,
        visitor_id: UUID | None,
        user_id: UUID | None,
        payload: dict[str, Any] | None,
        occurrence_key: UUID | None,
    ) -> None:
        event = AnalyticsEvent(
            event_name=event_name,
            visitor_id=visitor_id,
            occurrence_key=occurrence_key,
            user_id=user_id,
            event_time=self._clock.now(),
            payload=payload or {},
        )
        session = self._session_factory()
        try:
            await session.execute(insert_of(event))
            await session.commit()
        finally:
            await session.close()
