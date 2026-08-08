import pytest

from tests.frontend.abstract_frontend_test import AbstractFrontendTest


# RED 2026-08-08: there is no /documents/:id route at all. `frontend/src/app/App.tsx` routes
# only /register, /login, /verify, /auth/callback and a /* catch-all to DocumentGenerationFlow,
# so the editor route is not "missing a blocker" — it does not exist, and neither does the
# documents list its way-out link must lead to. Verified live against the running stack
# (backend :8000, frontend :80, both from infra/.env): a live session plus a random document
# id times out in _wait_for_visible on [data-testid='document-not-found'].
# Green-frontend scope is therefore three things, not one: the /documents/:id route, the
# not-found blocker, and a /documents list for the link to target.
# Un-skip in green-frontend for Story 19, Frontend Scenario 0.1.
@pytest.mark.skip(reason="RED: no /documents/:id route and no document-not-found blocker yet")
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
