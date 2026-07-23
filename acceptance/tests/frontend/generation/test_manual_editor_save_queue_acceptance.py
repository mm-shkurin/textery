from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestManualEditorSaveQueueAcceptance(AbstractFrontendTest):
    """UI Test Scenario 4.2 (Track B owe): an out-of-order save never shows stale content.

    Given a save is in flight
    When the visitor edits again while it is still saving
    Then that mid-flight edit queues a single re-save that fires with the latest content once the
      first settles
    And the persisted document reflects the latest edit, never the stale earlier one

    The jsdom test drove the queue with fake promises. This holds a real PUT in flight (network
    throttling), lands a real edit during that window — which is what arms the queue, via
    onUpdate -> noteEdit — then reads the backend to prove the newest content won AND counts the
    PUTs to prove exactly one re-save fired (not zero = dropped queue, not concurrent PUTs).
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

        # The mid-flight EDIT is what arms the queue (onUpdate -> noteEdit sets saveAgainRequested
        # while isSaving). Clicking Save again is a realistic user action but not the trigger —
        # the PUT-count assertion below is what proves the queued re-save actually fired.
        statements.type_more_in_editor(webdriver, "v2")
        statements.click_save(webdriver)
        statements.clear_network_throttle(webdriver)

        statements.wait_for_saved(webdriver)
        statements.assert_saved_content_is(webdriver, "v1v2")
        statements.assert_exactly_two_document_puts(webdriver)
