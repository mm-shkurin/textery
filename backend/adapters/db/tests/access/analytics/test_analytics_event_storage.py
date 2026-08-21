from statements.analytics_event_storage_statements import AnalyticsEventStorageStatements


class TestAnonymousEventIsRecordedAsAnonymous:
    """1.1 An event with no token is recorded as anonymous.

    Given a visitor with no session
    When it reports a site visit
    Then the event is recorded
    And the stored event has no account attached.

    The storage half of the scenario. The usecase test already pins that the right
    `AnalyticsEvent` is built and handed to the port -- against a Fake, so no column
    was involved. Here the port is the real Postgres adapter: the entity becomes a
    row, the row survives the commit, and it is read back on a connection of its own
    because `expire_on_commit=False` would otherwise serve the re-read from the
    writing session's identity map and pass on a row Postgres never received.

    Only the STORED path. ALREADY_RECORDED and CONFLICTING_NAME are the other two
    outcomes the port answers, and each has its own later scenario -- this one is the
    first-time anonymous insert and nothing else.
    """

    async def test_should_store_the_visit_with_no_account_attached(
        self, analytics_storage_statements: AnalyticsEventStorageStatements
    ):
        await analytics_storage_statements.when_a_visitor_with_no_session_reports_a_site_visit()

        analytics_storage_statements.assert_the_store_reported_a_new_row()
        await analytics_storage_statements.read_back_the_stored_events_on_a_fresh_connection()
        analytics_storage_statements.assert_the_event_is_recorded()
        analytics_storage_statements.assert_no_account_is_attached()
