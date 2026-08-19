from enum import Enum
from typing import Protocol

from analytics.analytics_event import AnalyticsEvent


class SaveOutcome(Enum):
    """What the store did with an event it was handed.

    A `-> None` port could not express the contract's 204-vs-409 branch, so the
    three outcomes land together as shape
    (`decisions/analytics-ingest-shape-decision.md`). Scenario 1.1 exercises only
    `STORED`; `ALREADY_RECORDED` (a repeat under the same name, answered 204) and
    `CONFLICTING_NAME` (the same key under a different name, answered 409) are
    asserted by §5.x, which is also where the usecase first branches on the value.
    """

    STORED = "STORED"
    ALREADY_RECORDED = "ALREADY_RECORDED"
    CONFLICTING_NAME = "CONFLICTING_NAME"


class AnalyticsEventRepository(Protocol):
    """Port for analytics-event persistence.

    Write-only, deliberately: `endpoints.md` ships no read surface ("reading is
    Story 15"), so this port grows no finder that a later story could quietly
    turn into an unscoped read of the whole table.
    """

    async def save_new(self, event: AnalyticsEvent) -> SaveOutcome:
        """Insert one event, reporting what the store decided.

        The implementor must decide the collapse with the insert itself
        (`INSERT ... ON CONFLICT (visitor_id, occurrence_key) DO NOTHING
        RETURNING id`), never with a prior read: a read-then-insert writes two
        rows when React StrictMode's double-fire arrives on two connections at
        the same instant, which is the ordinary case here rather than the rare
        one.
        """
        ...
