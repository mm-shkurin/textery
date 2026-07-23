"""Statements for the SAVE path of the manual editor's line breaks.

The line-break Selenium test proved the RENDER half — an Enter draws exactly one visual break
in a real browser. It never proved the SAVE half: that `editor.getHTML()` carries that break
into the PUT body and that the break survives the backend round-trip. A sanitizer or a parse
rule on either side could silently drop it, and the user would reopen a document with their
paragraphs run together — data loss the render assertion cannot see.

So this drives the break through a real save and reads it back through the backend's own
`GET /api/v1/documents/{id}`, using the same live session the browser authenticated with. The
freshly registered account owns exactly one document (created on editor mount), so the list
endpoint identifies it without the app exposing an id to the DOM.
"""

import os

import httpx
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from statements.frontend.base_frontend_statements import WAIT_TIMEOUT_SECONDS
from statements.frontend.generation.manual_editor_line_break_statements import (
    ManualEditorLineBreakStatements,
)
from statements.frontend.generation.manual_editor_statements import MANUAL_EDITOR_SELECTOR

SAVE_BUTTON = (By.CSS_SELECTOR, f"{MANUAL_EDITOR_SELECTOR} .me-save-btn")
SAVED_STATUS = (By.CSS_SELECTOR, f"{MANUAL_EDITOR_SELECTOR} .me-save-status--saved")

_ACCESS_TOKEN_KEY = "textery.auth.accessToken"
_REQUEST_TIMEOUT_SECONDS = 10
# ProseMirror's view-only caret helper never reaches the model, so getHTML never serializes it;
# assertions on the SAVED html need no caret-helper stripping, unlike the live-DOM ones.


def _backend_base_url() -> str:
    return f"http://localhost:{os.environ.get('BACKEND_PORT', '8000')}"


class ManualEditorSavePayloadStatements(ManualEditorLineBreakStatements):
    def save_document(self, driver) -> None:
        self._wait_for_visible(driver, SAVE_BUTTON).click()
        # The saved status is the only signal the PUT settled; asserting the payload before it
        # would race the request. me-save-status--saved renders exactly on a resolved clean save.
        WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(
            ec.visibility_of_element_located(SAVED_STATUS)
        )

    def read_back_saved_content(self, driver) -> str:
        """Fetch the just-saved document's content through the backend, not the browser.

        Reads the live access token the app stored in sessionStorage, lists this account's
        documents (exactly one), and reads it by id — the true round-trip a reopen would take.
        """
        token = driver.execute_script(
            "return window.sessionStorage.getItem(arguments[0]);", _ACCESS_TOKEN_KEY
        )
        assert token, "expected a live access token in sessionStorage after a live-session flow"
        headers = {"Authorization": f"Bearer {token}"}
        with httpx.Client(
            base_url=_backend_base_url(), timeout=_REQUEST_TIMEOUT_SECONDS, headers=headers
        ) as client:
            listing = client.get("/api/v1/documents")
            assert listing.status_code == 200, (
                f"list documents expected 200, got {listing.status_code}: {listing.text}"
            )
            items = listing.json()["items"]
            assert len(items) == 1, f"expected exactly one document for the fresh account, got {len(items)}"
            document_id = items[0]["document_id"]

            read = client.get(f"/api/v1/documents/{document_id}")
            assert read.status_code == 200, (
                f"read document expected 200, got {read.status_code}: {read.text}"
            )
        return read.json()["content"]

    def assert_saved_content_preserves_single_break(self, driver) -> None:
        content = self.read_back_saved_content(driver)
        break_count = content.count("<br>")
        assert break_count == 1, (
            f"expected exactly one <br> to survive the save round-trip, got {break_count} "
            f"in saved content {content!r}"
        )
        # Position-locked, not membership-blind: a global count + independent `"foo"`/`"bar"`
        # membership would both pass on `foobar<br>` — the exact run-together data loss this test
        # exists to catch (the break moved OUT from between the runs, a stray <br> left behind).
        # Assert the break sits BETWEEN the two runs.
        assert "foo<br>bar" in content, (
            f"expected the break to survive BETWEEN the two runs (foo<br>bar), got {content!r}"
        )
