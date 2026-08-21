"""Wiring for Story 14: the ingest route, server-side emission, and attribution.

Two things here are deliberately unlike every other slice in this package.

**The recorder and the context writer are handed the session FACTORY, not a
session.** Every other factory builds its usecase on the request-scoped session,
which is right for work the request's transaction owns. Analytics is the
opposite case: a failed analytics INSERT must not poison the transaction the
product is in the middle of, so it runs on a session of its own that is opened
and closed inside the call.

**A missing geolocation configuration is a boot that SUCCEEDS.** `create_geolocation`
answers `None`, the null object takes over, and `registration_country` is NULL for
every account this deployment creates. Recorded at boot as one line, rather than as
an exception, because refusing to start over an unset marketing column is exactly
the coupling this story's governing decision forbids
(`04_Infrastructure_Tests.md` §3.1).
"""

import logging
import os

from geolocation.http_geolocation import create_geolocation
from sqlalchemy.ext.asyncio import AsyncSession

from access.analytics.analytics_event_storage import SqlAlchemyAnalyticsEventRepository
from access.analytics.registration_context_storage import SqlAlchemyRegistrationContextWriter
from access.analytics.server_event_recorder import SqlAlchemyServerEventRecorder
from access.auth.oauth_rate_limit_storage import SqlAlchemyRateLimiter
from analytics.record_analytics_event import RecordAnalyticsEvent
from analytics.record_registration_context import RecordRegistrationContext
from analytics.registration_context import Geolocation, NullGeolocation
from container.runtime import request_scoped, session_factory
from session import SqlAlchemyUnitOfWork
from shared.clock import SystemClock

logger = logging.getLogger(__name__)

EVENT_RATE_LIMIT_ENV_VAR = "ANALYTICS_EVENT_RATE_LIMIT"
EVENT_RATE_WINDOW_ENV_VAR = "ANALYTICS_EVENT_RATE_WINDOW_SECONDS"
# 120 per 60 s, the bound `endpoints.md` names. A named default rather than a
# required variable: every deployment declares it (Infra §3.2, §3.4), and a
# deployment that forgets still runs with the documented number instead of
# unbounded.
DEFAULT_EVENT_RATE_LIMIT = 120
DEFAULT_EVENT_RATE_WINDOW_SECONDS = 60


def event_rate_limit() -> int:
    return _positive_int(EVENT_RATE_LIMIT_ENV_VAR, DEFAULT_EVENT_RATE_LIMIT)


def event_rate_window_seconds() -> int:
    return _positive_int(EVENT_RATE_WINDOW_ENV_VAR, DEFAULT_EVENT_RATE_WINDOW_SECONDS)


def _positive_int(variable: str, default: int) -> int:
    try:
        value = int(os.environ.get(variable, default))
    except ValueError:
        value = default
    # A zero or negative bound would refuse every event, which reads in
    # production as "analytics is broken" rather than as "the value is wrong".
    return value if value > 0 else default


# Built once at import, like `engine` and `token_service`: the client holds a
# connection pool, and one per request would leak a pool per registration.
_geolocation = create_geolocation()
if _geolocation is None:
    logger.info("no geolocation configured; registration_country stays unset")


@request_scoped
def create_record_analytics_event(session: AsyncSession) -> RecordAnalyticsEvent:
    return RecordAnalyticsEvent(
        analytics_event_repository=SqlAlchemyAnalyticsEventRepository(session),
        clock=SystemClock(),
        unit_of_work=SqlAlchemyUnitOfWork(session),
        # The OAuth legs' fixed-window counter, satisfying this port structurally
        # rather than by inheritance. On the request's session, which
        # `request_scoped` closes: the limiter commits its own increment as its
        # first statement, so the hit is already durable by the time the event is
        # refused or the insert fails (§6.7 -- refused events are COUNTED, not
        # merely dropped).
        rate_limiter=SqlAlchemyRateLimiter(
            session,
            max_requests=event_rate_limit(),
            window_seconds=event_rate_window_seconds(),
        ),
    )


def create_analytics_recorder() -> SqlAlchemyServerEventRecorder:
    return SqlAlchemyServerEventRecorder(session_factory=session_factory, clock=SystemClock())


def geolocation() -> Geolocation:
    """The configured lookup, or the null one. Never `None` to a caller.

    Exposed so the OAuth callback can build the same registration-context
    recorder the register route gets: an account created through a provider must
    carry the same technical context as one created with a password, and two
    places choosing their own geolocation is how the two drift apart.
    """
    return _geolocation or NullGeolocation()


def create_record_registration_context() -> RecordRegistrationContext:
    return RecordRegistrationContext(
        context_writer=SqlAlchemyRegistrationContextWriter(session_factory=session_factory),
        geolocation=geolocation(),
    )
