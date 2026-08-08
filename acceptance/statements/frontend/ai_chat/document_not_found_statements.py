"""Statements for UI scenario 0.1 — the not-found blocker on the AI-chat editor route.

Navigation note (`.claude/guidelines/frontend-rules.md`, "FORBIDDEN in-app navigation via
URL"): this scenario is reached by a direct `driver.get` of the editor route, which is the
rule's allowed exception (2) — an external entry point where users genuinely arrive by URL.

Two independent reasons, both true as of 2026-08-08:

1. No in-app path to this state can exist *by construction*. A documents list, once it
   ships, lists only documents that exist and belong to the signed-in user, so no sequence
   of clicks inside the app can ever select an absent or foreign document. The Given is
   only reachable from outside: a stale bookmark, or a link shared by another account.
2. No in-app path exists *yet*, either. There is no documents-list screen in the app at
   all, and `frontend/src/app/App.tsx` has no `/documents/:id` route — that path currently
   falls through the `/*` catch-all to `DocumentGenerationFlow`. So there is presently no
   UI to click even for the documents that do exist.

Re-check obligation: reason (2) expires the moment the documents list ships. Reason (1) is
the load-bearing one and is expected to survive, but when the list lands, re-verify that it
offers no click path to a foreign or deleted document (for example, a "recently deleted"
row or a shared-with-me tab). If such a path appears, replace the `driver.get` below with
UI-click navigation.
"""

import uuid

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from statements.frontend.base_frontend_statements import BaseFrontendStatements

NOT_FOUND_BLOCKER = (By.CSS_SELECTOR, "[data-testid='document-not-found']")
NOT_FOUND_TITLE = (By.CSS_SELECTOR, "[data-testid='document-not-found-title']")
NOT_FOUND_DOCUMENTS_LINK = (
    By.CSS_SELECTOR, "[data-testid='document-not-found-documents-link']"
)
MANUAL_EDITOR = (By.CSS_SELECTOR, "[data-testid='manual-editor']")

# Prefix, not an exact testid, and deliberately so. No chat-panel element exists yet, so an
# exact-match absence check (`[data-testid='ai-chat-panel']`) would be vacuous forever: it
# would keep passing no matter what scenario 1.1 later names the panel. Matching the whole
# `ai-chat-*` testid namespace means no naming choice in 1.1 can slip past this assertion.
AI_CHAT_ANY = (By.CSS_SELECTOR, "[data-testid^='ai-chat']")

# The documents-list route this scenario's way-out link must lead to. No such route exists
# yet; this test is the specification that defines it, and green-frontend must match.
DOCUMENTS_LIST_PATH = "/documents"

EXPECTED_NOT_FOUND_TITLE = "Документ не найден"
EXPECTED_DOCUMENTS_LINK_TEXT = "К моим документам"


class DocumentNotFoundStatements(BaseFrontendStatements):
    def open_editor_for_an_absent_document(self, driver: WebDriver, app_url: str) -> None:
        """Arrive on the editor route for a document id that exists for nobody.

        A random UUID is indistinguishable, from the client's side, from a document that
        belongs to another account: the story's endpoints answer both with the same 404
        body (`endpoints.md`, "All seven endpoints share one 404 body"), so one fixture
        covers both halves of the Given.

        A live session, not a seeded one: the route loads the document over the API on
        mount, and a fake token 401s there — the client would clear the session and collapse
        to the landing, which is a different screen from the blocker under test.
        """
        self._establish_logged_in_precondition(driver, app_url, live_session=True)
        driver.get(f"{app_url}{DOCUMENTS_LIST_PATH}/{uuid.uuid4()}")

    def assert_not_found_blocker_is_shown(self, driver: WebDriver) -> None:
        blocker = self._wait_for_visible(driver, NOT_FOUND_BLOCKER)
        assert blocker.is_displayed(), "expected the not-found blocker to be displayed"
        self._assert_element_text_equals(
            driver, NOT_FOUND_TITLE, EXPECTED_NOT_FOUND_TITLE, "not-found blocker title"
        )

    def assert_editor_and_chat_panel_are_not_shown(self, driver: WebDriver) -> None:
        # Ordered after the blocker has been waited for, so the absence checks cannot pass
        # vacuously by running before the route has rendered anything at all.
        self._wait_for_visible(driver, NOT_FOUND_BLOCKER)
        self._assert_absent(driver, MANUAL_EDITOR, "editor")
        self._assert_absent(driver, AI_CHAT_ANY, "chat panel element")

    def assert_documents_list_link_is_offered(self, driver: WebDriver, app_url: str) -> None:
        # The link must live inside the blocker: a stray documents link elsewhere in the
        # chrome would otherwise satisfy "a way out" that the blocker itself never offers.
        blocker = self._wait_for_visible(driver, NOT_FOUND_BLOCKER)
        assert blocker.find_elements(*NOT_FOUND_DOCUMENTS_LINK), (
            "expected the documents-list link to be inside the not-found blocker"
        )
        self._assert_element_text_equals(
            driver,
            NOT_FOUND_DOCUMENTS_LINK,
            EXPECTED_DOCUMENTS_LINK_TEXT,
            "documents-list link",
        )
        self._assert_link_target(
            driver,
            NOT_FOUND_DOCUMENTS_LINK,
            app_url,
            DOCUMENTS_LIST_PATH,
            "documents-list link",
        )
