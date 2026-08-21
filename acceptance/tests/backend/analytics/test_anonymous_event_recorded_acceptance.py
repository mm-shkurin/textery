import pytest

from tests.backend.abstract_backend_test import AbstractBackendTest


@pytest.mark.skip(
    reason="RED: POST /api/v1/analytics/events is registered on no router and no "
    "migration creates the table, so the call answers Starlette's route-miss 404 "
    "and the fresh read raises UndefinedTableError: relation \"analytics_events\" "
    "does not exist"
)
class TestAnonymousEventIsRecordedWithoutAnAccount(AbstractBackendTest):
    """Scenario 1.1: An event with no token is recorded as anonymous.

    Given a visitor with no session
    When it reports a site visit
    Then the event is recorded
    And the stored event has no account attached.
    """

    async def test_an_event_with_no_token_is_recorded_as_anonymous(
        self, analytics_ingest_statements
    ):
        visit = await analytics_ingest_statements.given_a_visitor_with_no_session_reports_a_site_visit()

        analytics_ingest_statements.assert_the_event_is_recorded(visit)
        analytics_ingest_statements.assert_no_account_is_attached(visit)
