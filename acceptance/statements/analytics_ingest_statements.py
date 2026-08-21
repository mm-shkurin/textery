"""Statements for the analytics ingest route, scenario 1.1 (`01_API_Tests.md` §1.1).

A visitor with no session reports a site visit, and the claim is about the row the
database ends up holding — not about the answer. The preamble of `01_API_Tests.md` is
explicit: "«an event is recorded» never means «the call answered 200». Every emitter in
this story hangs off a path that returns success without writing." So the response is
captured and reported in every failure message — a 404 or a 401 is the first thing you
want to see when nothing was stored — and it is never asserted. Scenario 1.3, where the
refusal itself is the claim, is where a status code becomes an assertion.

The stored row is fetched through `analytics_event_probe`, on its own connection in
this process: `endpoints.md` ships no read endpoint ("reading is Story 15"), and a
re-read inside the writing session would be served from SQLAlchemy's identity map.

`visitor_id` and `occurrence_key` are minted fresh per invocation. Sharing a fixture
UUID across runs would let a row written by an earlier run satisfy "the event is
recorded" for a run that stored nothing.

Every assertion below routes through `_the_one_stored_event`, so no claim about a
column can be reached unless exactly one row exists for the visitor. A read that
returned nothing fails on the cardinality, naming the visitor and the occurrence, and
never reaches an `is None` that would have read as success.
"""

import uuid
from dataclasses import dataclass

from clients.application.application_client import ApplicationClient
from clients.application.dto.analytics.analytics_event_dtos import (
    AnalyticsEventRequestDto,
    AnalyticsEventResponseDto,
)
from clients.database import analytics_event_probe
from clients.database.analytics_event_probe import StoredAnalyticsEvent


@dataclass(frozen=True)
class ReportedSiteVisit:
    visitor_id: uuid.UUID
    occurrence_key: uuid.UUID
    response: AnalyticsEventResponseDto
    stored: tuple[StoredAnalyticsEvent, ...]

    def identity(self) -> str:
        """The visitor and occurrence every failure message has to name."""
        return (
            f"visitor_id={self.visitor_id} occurrence_key={self.occurrence_key} "
            f"(the route answered status_code={self.response.status_code}, "
            f"body={self.response.body!r})"
        )


class AnalyticsIngestStatements:
    # The browser-origin name for a page view (analytics_events_create.yaml).
    SITE_VISITED = "SITE_VISITED"

    def __init__(self, client: ApplicationClient):
        self._client = client

    async def given_a_visitor_with_no_session_reports_a_site_visit(
        self,
    ) -> ReportedSiteVisit:
        visitor_id = uuid.uuid4()
        occurrence_key = uuid.uuid4()
        # access_token=None sends no Authorization header at all — "a visitor with no
        # session" is the absence of the header, not an empty one.
        response = await self._client.record_analytics_event(
            AnalyticsEventRequestDto(
                event_name=self.SITE_VISITED,
                visitor_id=str(visitor_id),
                occurrence_key=str(occurrence_key),
            ),
            access_token=None,
        )
        return ReportedSiteVisit(
            visitor_id=visitor_id,
            occurrence_key=occurrence_key,
            response=response,
            stored=await analytics_event_probe.read_events_for(visitor_id),
        )

    def assert_the_event_is_recorded(self, visit: ReportedSiteVisit) -> None:
        stored = self._the_one_stored_event(visit)
        # The occurrence key comes back from the row rather than out of the
        # lookup, so this compares what was STORED against what was SENT.
        # Compared as UUID values and reported with `!r`, so a key kept as text —
        # the defect §5.6 names — shows up as `'…'` against `UUID('…')` rather
        # than as an equal-looking mismatch.
        assert stored.occurrence_key == visit.occurrence_key, (
            f"expected the stored event to carry the occurrence key it was "
            f"reported under, got occurrence_key={stored.occurrence_key!r} "
            f"for {visit.identity()}"
        )
        assert stored.event_name == self.SITE_VISITED, (
            f"expected the stored event to be recorded as {self.SITE_VISITED!r}, got "
            f"event_name={stored.event_name!r} for {visit.identity()}"
        )

    def assert_no_account_is_attached(self, visit: ReportedSiteVisit) -> None:
        stored = self._the_one_stored_event(visit)
        # `analytics_events.user_id IS NULL`, per the DSL Technical Reference. An
        # anonymous event carries no account at all — not some placeholder account,
        # and not a value that merely differs from a signed-in caller's. NULL is the
        # exact expected value here, not an existence check: any other value, of any
        # type, fails, and a run where no row was stored failed one line above.
        assert stored.user_id is None, (
            f"expected the stored event to carry no account (user_id IS NULL), got "
            f"user_id={stored.user_id!r} for {visit.identity()}"
        )

    def _the_one_stored_event(self, visit: ReportedSiteVisit) -> StoredAnalyticsEvent:
        # One request from a visitor minted for this call means one row for that
        # visitor — counted across the visitor's WHOLE history, not across the subset
        # already matching the occurrence key, so a second row written under a key the
        # caller never sent is a failure here rather than an invisible extra.
        assert len(visit.stored) == 1, (
            f"expected exactly one stored event for {visit.identity()}, got "
            f"{len(visit.stored)}: {visit.stored!r}"
        )
        return visit.stored[0]
