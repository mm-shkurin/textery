from statements.analytics_payload_storage_statements import AnalyticsPayloadStorageStatements


class TestPayloadSurvivesStoreAndRead:
    """3.6 A payload survives store and read with its values unchanged.

    Given a visitor reporting a visit that carries a payload
    When the event is stored
    Then a different connection reads the payload back exactly as it was reported
    And the degraded marker it was reported with is the one that was stored.

    Written after the adapter was found dropping both columns. The INSERT omitted
    them while the entity did not carry them yet, and the column defaults (`{}` /
    false) are precisely the values an event WITHOUT them has -- so nothing read
    wrong, and nothing kept reading wrong once the entity grew the fields, until a
    request finally carried a payload and the stored row was still empty. A default
    that agrees with the absent case cannot tell "carried nothing" from "carried
    something that was dropped"; only an event that carries something can.
    """

    async def test_should_store_the_payload_and_the_marker_exactly_as_reported(
        self, analytics_payload_statements: AnalyticsPayloadStorageStatements
    ):
        await analytics_payload_statements.when_a_visitor_reports_a_visit_carrying_a_payload()

        await analytics_payload_statements.read_back_the_stored_events_on_a_fresh_connection()
        analytics_payload_statements.assert_the_payload_is_stored_exactly_as_reported()
