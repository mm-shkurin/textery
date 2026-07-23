from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestManualEditorSaveQueueAcceptance(AbstractFrontendTest):
    """UI Test Scenario 4.2 (Track B owe): an out-of-order save never shows stale content.

    Given a save is in flight
    When the visitor edits again and requests another save (real clicks)
    Then the second save is queued and fires with the latest content once the first settles
    And the persisted document reflects the latest edit, never the stale earlier one

    The jsdom test drove the queue with fake promises. This exercises it through a real click
    while a real PUT is in flight (held open by network throttling), then reads the backend to
    prove the newest content won.
    """

    def test_should_persist_the_latest_edit_when_a_save_is_queued_behind_another(
        self, webdriver, app_url, manual_editor_save_queue_statements
    ):
        statements = manual_editor_save_queue_statements
        statements.open_manual_editor_for_doklad(webdriver, app_url)

        statements.type_text_in_editor(webdriver, "v1")
        statements.throttle_network(webdriver)
        statements.click_save(webdriver)
        statements.wait_for_save_in_flight(webdriver)

        # Edit again and request a second save WHILE the first PUT is still open — the design
        # queues this rather than firing a concurrent request.
        statements.type_more_in_editor(webdriver, "v2")
        statements.click_save(webdriver)
        statements.clear_network_throttle(webdriver)

        statements.wait_for_saved(webdriver)
        statements.assert_saved_content_is(webdriver, "v1v2")
