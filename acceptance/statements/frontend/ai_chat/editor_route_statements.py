"""Shared browser steps for every UI scenario that opens the AI-chat editor route.

Extracted when scenario 1.1 needed the same three things scenario 0.2 already had: sign in
as ONE named account, reach `/documents/:id` by CLICKING the account's row in the documents
list, and resolve an element INSIDE the chat panel. Copying them would have left two files
that must be kept in agreement about the auth-session keys, the documents-list route and the
panel's testid.

Navigation note (`.claude/guidelines/frontend-rules.md`, "FORBIDDEN in-app navigation via
URL"): the Given of these scenarios — *the user opens a document* — is performed by a CLICK
on the document's row, never by typing the editor URL. The one `driver.get` here is of the
LIST, `/documents`, which stands on the rule's allowed exception (2): a bookmarkable entry
point, and today the only way in — `App.tsx` registers `/documents` as a bare route and no
chrome links to it.

**Re-check obligation.** That reason expires the moment any navigable element (header link,
breadcrumb, landing card) points at `/documents` — scenario 7.2 is the likeliest to add one.
Re-verify then; if a click path into the list exists, click it instead of this `driver.get`.
"""

from typing import Protocol

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait

from statements.frontend.base_frontend_statements import (
    WAIT_TIMEOUT_SECONDS,
    BaseFrontendStatements,
)

DOCUMENTS_LIST_PATH = "/documents"
HISTORY_PAGE = (By.CSS_SELECTOR, "[data-testid='history-page']")
DOCUMENT_ROW = (By.CSS_SELECTOR, "[data-testid='history-document-row']")

# Required of each document row so the click below can be pinned to the document the setup
# created, rather than merely to "the only row present".
DOCUMENT_ID_ATTRIBUTE = "data-document-id"
EXPECTED_DOCUMENT_ROW_COUNT = 1

CHAT_PANEL = (By.CSS_SELECTOR, "[data-testid='ai-chat-panel']")
MESSAGE_INPUT = (By.CSS_SELECTOR, "[data-testid='ai-chat-message-input']")
SEND_BUTTON = (By.CSS_SELECTOR, "[data-testid='ai-chat-send-button']")


class EditorAccount(Protocol):
    """What the steps below need of a scenario's setup result: a real session, one document.

    A Protocol rather than a base dataclass — each scenario's setup carries its own extra
    facts (0.2's `resets_at`, 1.1's stored content) and nothing here should know about them.
    """

    access_token: str
    refresh_token: str
    document_id: str


class EditorRouteStatements(BaseFrontendStatements):
    def _sign_in_as(self, driver: WebDriver, app_url: str, account: EditorAccount) -> None:
        """Load the origin, then put THIS account's real tokens in sessionStorage.

        The base class's `_establish_logged_in_precondition` cannot serve here: its live
        grade issues a session of its own, and these scenarios must sign in as the one
        account whose document the setup prepared.
        """
        driver.get(app_url)
        self._seed_session_tokens(driver, account.access_token, account.refresh_token)

    def _open_the_only_document_by_clicking_it(
        self, driver: WebDriver, app_url: str, account: EditorAccount
    ) -> None:
        driver.get(f"{app_url}{DOCUMENTS_LIST_PATH}")
        self._wait_for_visible(driver, HISTORY_PAGE)
        rows = driver.find_elements(*DOCUMENT_ROW)
        # Each setup gives its account exactly ONE document precisely so this holds: with a
        # second row the click below could open a document the scenario knows nothing about.
        assert len(rows) == EXPECTED_DOCUMENT_ROW_COUNT, (
            f"expected the account under test to own exactly {EXPECTED_DOCUMENT_ROW_COUNT} "
            f"document, found {len(rows)} rows in the documents list"
        )
        # Identity, not just arity: the count alone is satisfied by one row for some OTHER
        # document, leaving the URL check below to diagnose the click far downstream of it.
        actual_document_id = rows[0].get_attribute(DOCUMENT_ID_ATTRIBUTE) or ""
        assert actual_document_id == account.document_id, (
            f"expected the only documents-list row to carry {DOCUMENT_ID_ATTRIBUTE}="
            f"'{account.document_id}' (the document the setup prepared), "
            f"got '{actual_document_id}'"
        )
        rows[0].click()
        self._assert_url_path(driver, app_url, f"{DOCUMENTS_LIST_PATH}/{account.document_id}")

    def _chat_panel_descendant(
        self, driver: WebDriver, locator: tuple[str, str], label: str
    ) -> WebElement:
        """Resolve `locator` INSIDE the chat panel, waiting for the panel first.

        Anchoring on the panel does two jobs: nothing can pass vacuously against a route
        that has not rendered yet, and a same-named element elsewhere in the page chrome
        cannot stand in for the chat panel's own.

        **The wait is panel-scoped, and must stay so.** It used to be
        `self._wait_for_visible(driver, locator)` — a DOCUMENT-wide condition, which broke the
        method's own contract in both directions: a same-named element visible anywhere else on
        the page satisfied it while the panel still held none, leaving the count assertion below
        to run unsynchronised and fail with 0 on a panel a few milliseconds late; and when the
        only match was outside the panel the failure named the count rather than the scope.
        Polling `panel.find_elements` is what makes the wait and the resolution agree.

        Only DISPLAYED descendants count. A rendered-but-hidden element must not be able to
        stand in for one the user can see — every caller goes on to assert something (enabled,
        text, open) that a hidden element would satisfy or silently distort.
        """
        panel = self._wait_for_visible(driver, CHAT_PANEL)
        matches = WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(
            lambda _: [e for e in panel.find_elements(*locator) if e.is_displayed()],
            f"expected a visible {label} inside the chat panel, found none",
        )
        assert len(matches) == 1, (
            f"expected exactly one visible {label} inside the chat panel, found {len(matches)}"
        )
        return matches[0]
