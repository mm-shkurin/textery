from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestDocumentNotFoundBlockerAcceptance(AbstractFrontendTest):
    """UI Test Scenario 0.1: A document that cannot be loaded blocks the chat panel with a
    way out.

    Given the editor is opened for a document that is absent or not the user's
    When the page loads
    Then a not-found blocker is shown instead of the editor and chat panel
    And a link back to the documents list is offered
    """

    def test_should_block_with_not_found_and_offer_the_documents_list(
        self, webdriver, app_url, document_not_found_statements
    ):
        document_not_found_statements.open_editor_for_an_absent_document(webdriver, app_url)

        document_not_found_statements.assert_not_found_blocker_is_shown(webdriver)
        document_not_found_statements.assert_editor_and_chat_panel_are_not_shown(webdriver)
        document_not_found_statements.assert_documents_list_link_is_offered(webdriver, app_url)
