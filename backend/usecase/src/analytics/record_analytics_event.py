import logging
from typing import Any, Protocol
from uuid import UUID

from analytics.analytics_error_codes import (
    INVALID_OCCURRENCE_KEY,
    INVALID_OCCURRENCE_KEY_MESSAGE,
    INVALID_VISITOR_ID,
    INVALID_VISITOR_ID_MESSAGE,
    OCCURRENCE_KEY_CONFLICT,
    OCCURRENCE_KEY_CONFLICT_MESSAGE,
    RATE_LIMITED,
    RATE_LIMITED_MESSAGE,
    UNKNOWN_EVENT_NAME,
    UNKNOWN_EVENT_NAME_MESSAGE,
)
from analytics.analytics_event import AnalyticsEvent
from analytics.analytics_event_repository import AnalyticsEventRepository, SaveOutcome
from analytics.analytics_payload import validate_payload
from analytics.event_names import BROWSER_ORIGIN_EVENT_NAMES
from shared.clock import Clock
from shared.exceptions import ValidationException
from shared.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


class EventRateLimiter(Protocol):
    """A shared, cross-instance bound on how fast one source may report events.

    Declared here rather than imported from the OAuth legs' limiter: the two are
    the same shape by coincidence of both being fixed-window counters, and an
    import would mean a change made for the sign-in budget silently retunes
    analytics. Structural typing means one adapter still satisfies both.

    Returning `False` -- rather than raising -- is what lets §6.3 hold: a limiter
    that cannot answer refuses the event, and refusing is this port's normal
    vocabulary rather than an exception path the caller might forget.
    """

    async def register_hit(self, bucket_key: str, now: Any) -> bool: ...


class AllowAllEventRateLimiter:
    async def register_hit(self, bucket_key: str, now: Any) -> bool:
        return True


class RecordAnalyticsEvent:
    """Record one client-origin analytics event.

    `user_id` is a parameter, never a field of the reported event: the caller
    resolves it from the Authorization header, so a client cannot attribute its
    own events to somebody else's account by putting an id in the body. `None`
    means the header was absent -- scenario 1.1. A header that was sent and did
    not resolve never reaches here at all (§1.3).

    Everything this usecase refuses, it refuses BEFORE the insert and with a
    message that repeats none of the input. This is the product's only tokenless
    write; its errors reach anyone.
    """

    def __init__(
        self,
        analytics_event_repository: AnalyticsEventRepository,
        clock: Clock,
        unit_of_work: UnitOfWork,
        rate_limiter: EventRateLimiter | None = None,
    ) -> None:
        self._analytics_event_repository = analytics_event_repository
        self._clock = clock
        self._unit_of_work = unit_of_work
        self._rate_limiter = rate_limiter or AllowAllEventRateLimiter()

    async def execute(
        self,
        user_id: UUID | None,
        event_name: str,
        visitor_id: str,
        occurrence_key: str,
        payload: dict[str, Any] | None = None,
        degraded: bool = False,
        source: str = "",
    ) -> None:
        """`visitor_id` and `occurrence_key` arrive as the raw strings the request
        carried -- the DTO types them permissively so a bad value reaches the
        domain and returns the canonical 400 rather than Pydantic's 422, which
        would echo the rejected input back on the product's only tokenless route.
        """
        await self._guard_the_rate(source)
        event = AnalyticsEvent(
            event_name=self._accepted_name(event_name),
            # Parsed, not stored as text: the entity types both identifiers as
            # `UUID` so the four spellings of one visitor id (§2.4) resolve to
            # one value before anything downstream sees them.
            visitor_id=self._identifier(visitor_id, INVALID_VISITOR_ID, INVALID_VISITOR_ID_MESSAGE),
            occurrence_key=self._identifier(
                occurrence_key, INVALID_OCCURRENCE_KEY, INVALID_OCCURRENCE_KEY_MESSAGE
            ),
            # Straight through from the caller. The usecase never reads an id
            # out of the reported event, so a client cannot attribute its
            # events to another account.
            user_id=user_id,
            # The injected Clock, never `datetime.now()` -- that is what keeps
            # every later time-dependent scenario controllable.
            event_time=self._clock.now(),
            payload=validate_payload(payload),
            # The one field a client is trusted with, because only the browser
            # knows its own storage failed. Nothing downstream decides anything
            # on it: it marks a row as one page load rather than one person, so
            # Story 15 can leave it out of unique-visitor counts (§4.1, §4.2).
            degraded=bool(degraded),
        )
        outcome = await self._analytics_event_repository.save_new(event)
        if outcome is SaveOutcome.CONFLICTING_NAME:
            # Not a replay of anything: the same key under a different name is a
            # client bug or a probe, and collapsing it would silently discard a
            # real event while answering success (`endpoints.md` § five
            # decisions, 2). Nothing is stored and the first row is untouched.
            raise ValidationException(
                message=OCCURRENCE_KEY_CONFLICT_MESSAGE, error_code=OCCURRENCE_KEY_CONFLICT
            )
        # «The event is recorded» means durable: the acceptance test reads the
        # row back on a separate connection, where an uncommitted insert is
        # invisible. Committed for ALREADY_RECORDED too -- there is nothing to
        # write, and answering 204 without closing the transaction would leave
        # the read-after-write guarantee resting on an open one.
        await self._unit_of_work.commit()

    async def _guard_the_rate(self, source: str) -> None:
        """Refuse before anything is parsed, and fail CLOSED.

        The opposite of every other analytics guard in this story, deliberately.
        Elsewhere a failure costs an analytics row; here a limiter that cannot
        answer is the one case where letting the request through costs the
        database (§6.3). `source` is already a non-reversible digest of the
        caller's address by the time it arrives -- the counters must not become a
        visitor log (`03_Security_Tests.md` §5.2).

        The bucket is prefixed, so a flood of events can never spend the sign-in
        allowance the same address has (§6.2).
        """
        try:
            bucket = f"analytics:{source}"
            within_limit = await self._rate_limiter.register_hit(bucket, self._clock.now())
        except Exception as error:
            logger.warning("analytics rate limiter did not answer; refusing the event")
            raise ValidationException(
                message=RATE_LIMITED_MESSAGE, error_code=RATE_LIMITED
            ) from error
        if not within_limit:
            raise ValidationException(message=RATE_LIMITED_MESSAGE, error_code=RATE_LIMITED)

    def _accepted_name(self, event_name: object) -> str:
        """One of the three names a browser legitimately produces, or a refusal.

        The catalogue has twelve and the column's CHECK constraint lists all
        twelve, so a later story can emit the subscription names without a
        migration. The ROUTE accepts three: on a tokenless endpoint, "no client
        is allowed to send the others" is not a rule unless something refuses
        them.
        """
        if event_name not in BROWSER_ORIGIN_EVENT_NAMES:
            raise ValidationException(
                message=UNKNOWN_EVENT_NAME_MESSAGE, error_code=UNKNOWN_EVENT_NAME
            )
        return str(event_name)

    def _identifier(self, raw: object, error_code: str, message: str) -> UUID:
        """Parse one wire identifier, refusing anything that is not a UUID.

        `isinstance` FIRST: `uuid.UUID(3)` raises `AttributeError`, and
        `uuid.UUID(None)` a `TypeError` -- neither is a `ValueError`, so a
        `except ValueError` alone would let a JSON number out of here as a 500 on
        the one route that has no token in front of it.
        """
        if not isinstance(raw, str):
            raise ValidationException(message=message, error_code=error_code)
        try:
            return UUID(raw)
        except ValueError as error:
            raise ValidationException(message=message, error_code=error_code) from error
