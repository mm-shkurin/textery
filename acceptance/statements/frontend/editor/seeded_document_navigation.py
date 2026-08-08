"""Open a document that was seeded over HTTP, by clicking, as a user would.

Split out of `pagination_measuring_statements.py` so that file stays under the 200-line cap and
keeps to one subject (reading the pre-layout state). Reaching the editor is a separate subject and
one that scenarios 1.2, 1.3 and 2.x will each need, so it is a mixin rather than a private method.

UI-only navigation (`.claude/guidelines/frontend-rules.md`): the app root is the sole allowed
direct URL and everything after it is a click. There is no editor URL to type even if typing one
were allowed — story 18 put the create path on `mode='auto'`, leaving `openDocumentFromHistory`
as the only branch that mounts the editor for an existing document, and it sets internal flow
state rather than a route.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from statements.frontend.editor.live_document_setup import SeededDocument

HEADER_HISTORY_BUTTON = (By.CSS_SELECTOR, "[data-testid='header-history-button']")
HISTORY_PAGE = (By.CSS_SELECTOR, "[data-testid='history-page']")
HISTORY_DOCUMENT_ROW = (By.CSS_SELECTOR, "[data-testid='history-document-row']")

# The row's title span (HistoryPage.tsx). Located by class because the span carries no testid and
# adding one would be production code, which a RED phase may not write. Asserting the title is how
# the test knows it opened the SEEDED document rather than merely "some row" — without it, an
# editor opened on the wrong document satisfies every downstream assertion.
HISTORY_ROW_TITLE = (By.CSS_SELECTOR, "[data-testid='history-document-row'] .history-row-title")

# The seeded account owns exactly one document, so the single row IS the seeded one. Pinned so
# that a setup which silently created two (or zero) fails HERE, naming the setup, rather than
# downstream as an unrecognisable assertion about the measuring state.
EXPECTED_HISTORY_ROW_COUNT = 1


class SeededDocumentNavigationMixin:
    """Sign in as the seeded document's owner and open it from Мои работы."""

    def open_the_seeded_document_in_the_editor(
        self, driver: WebDriver, app_url: str, document: SeededDocument
    ) -> None:
        """Reach the editor by clicking — Мои работы, then the seeded row.

        The session is the SEEDED document's owner, passed through rather than minted here;
        `issue_live_session` would otherwise create a second account whose history is empty.
        """
        self._establish_logged_in_precondition(driver, app_url, session=document.session)
        driver.get(app_url)
        self._wait_for_visible(
            driver,
            HEADER_HISTORY_BUTTON,
            "expected the header to offer Мои работы for a logged-in owner, but the history "
            "button never appeared — the seeded session did not take",
        ).click()
        self._wait_for_visible(driver, HISTORY_PAGE, "expected Мои работы to open")
        self._assert_history_lists_only_the_seeded_document(driver, document)
        self._open_the_only_history_row(driver)

    def _assert_history_lists_only_the_seeded_document(
        self, driver: WebDriver, document: SeededDocument
    ) -> None:
        """Exactly one row, and it is the seeded document — checked before anything is clicked."""
        self._wait_for_visible(
            driver,
            HISTORY_DOCUMENT_ROW,
            "expected the seeded document to be listed in Мои работы, but no row appeared",
        )
        self._assert_visible_element_count(
            driver, HISTORY_DOCUMENT_ROW, EXPECTED_HISTORY_ROW_COUNT, "history document row(s)"
        )
        self._assert_element_text_equals(
            driver, HISTORY_ROW_TITLE, document.title, "the history row's title"
        )

    def _open_the_only_history_row(self, driver: WebDriver) -> None:
        self._wait_for_visible(driver, HISTORY_DOCUMENT_ROW).click()
