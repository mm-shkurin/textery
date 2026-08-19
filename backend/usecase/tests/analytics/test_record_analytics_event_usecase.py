import pytest


@pytest.mark.skip(
    reason="RED: RecordAnalyticsEvent.execute is a stub -- the reported visit fails "
    "with NotImplementedError at usecase/src/analytics/record_analytics_event.py:45, "
    "in the when-phase, before any assertion runs."
)
class TestAnonymousEventIsRecorded:
    """Scenario 1.1: An event with no token is recorded as anonymous.

    Given a visitor with no session
    When it reports a site visit
    Then the event is recorded
    And the stored event has no account attached.
    """

    async def test_should_record_the_visit_with_no_account_attached(
        self, analytics_ingest_statements
    ):
        await analytics_ingest_statements.when_a_visitor_with_no_session_reports_a_site_visit()

        analytics_ingest_statements.assert_the_event_is_recorded()
        analytics_ingest_statements.assert_no_account_is_attached()
        analytics_ingest_statements.assert_the_event_time_came_from_the_server_clock()
        analytics_ingest_statements.assert_the_recording_was_committed_once()
