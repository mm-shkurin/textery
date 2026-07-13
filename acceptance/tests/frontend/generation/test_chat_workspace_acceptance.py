import pytest

from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestChatWorkspaceAcceptance(AbstractFrontendTest):
    """UI Test Scenario 4.1: The generation form displays the input fields for the
    chosen type.

    Deviates from the original spec text per known-debt #8: the standalone
    generation-form page was replaced by a single doc-left/chat-right screen. This
    scenario now covers the chat panel's initial state after the mode modal: a single
    free-text composer (mapped to `topic` on submit) ready to accept the visitor's
    first message.

    Given a visitor has selected "Доклад" and "Автоматический режим"
    Then the chat panel is visible
    And a free-text topic input is visible and empty
    And the send button is visible but disabled until text is entered
    """

    def test_should_display_chat_workspace_initial_state(self, webdriver, app_url, chat_workspace_statements):
        chat_workspace_statements.navigate_to_chat_workspace_for_doklad(webdriver, app_url)

        chat_workspace_statements.assert_chat_panel_is_visible(webdriver)
        chat_workspace_statements.assert_topic_input_is_visible_and_empty(webdriver)
        chat_workspace_statements.assert_send_button_is_visible_and_disabled(webdriver)
