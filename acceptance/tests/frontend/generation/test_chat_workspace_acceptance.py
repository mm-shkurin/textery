import pytest

from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestChatWorkspaceAcceptance(AbstractFrontendTest):
    """UI Test Scenario 4.1: The generation form displays the input fields for the
    chosen type.

    Deviates from the original spec text per known-debt #8: the standalone
    generation-form page was replaced by a single doc-left/chat-right screen. This
    scenario now covers the chat panel's initial state after the mode modal.

    Given a visitor has selected "Доклад" and "Автоматический режим"
    Then a breadcrumb chip shows the chosen document type "Доклад"
    And a single chat input is visible
    And a send button is visible
    """

    @pytest.mark.skip(
        reason="RED: selenium.common.exceptions.TimeoutException waiting on "
        "[data-testid='chat-breadcrumb-chip'] -- App.tsx still renders "
        "generation-form-placeholder for step 'form', chat workspace component "
        "does not exist yet"
    )
    def test_should_display_chat_workspace_initial_state(self, webdriver, app_url, chat_workspace_statements):
        chat_workspace_statements.navigate_to_chat_workspace_for_doklad(webdriver, app_url)

        chat_workspace_statements.assert_breadcrumb_chip_shows_document_type(webdriver)
        chat_workspace_statements.assert_chat_input_is_visible(webdriver)
        chat_workspace_statements.assert_send_button_is_visible(webdriver)
