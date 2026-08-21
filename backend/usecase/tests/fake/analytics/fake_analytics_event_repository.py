from analytics.analytics_event import AnalyticsEvent
from analytics.analytics_event_repository import SaveOutcome


class FakeAnalyticsEventRepository:
    """In-memory stand-in for the analytics-event store.

    Every event handed to it is kept, in call order, so a test can assert the
    cardinality as well as the columns: "one visit was reported" must mean one
    recorded event, and a usecase that recorded twice has to fail here rather
    than pass a "the row is there" check.

    Always answers `STORED`. The collapse of a repeated `occurrence_key` and the
    conflicting-name refusal are decided by the real statement's `ON CONFLICT`,
    and the fake grows them with §5.x -- the scenarios that assert them. Teaching
    it those rules now would be unasserted behaviour in test infrastructure.
    """

    def __init__(self) -> None:
        self.recorded: list[AnalyticsEvent] = []

    async def save_new(self, event: AnalyticsEvent) -> SaveOutcome:
        self.recorded.append(event)
        return SaveOutcome.STORED
