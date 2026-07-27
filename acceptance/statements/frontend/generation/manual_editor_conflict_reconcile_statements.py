"""Statements for the live 409 version-conflict reconcile (Editor Extension E3.4 / H9.5).

The jsdom conflict tests (`documentApi.conflict.test.ts`) prove the refetch-and-retry protocol
under mocked `fetch`: a 409 makes `saveDocument` GET the current version and re-PUT once. They
can never prove it end to end, because the 409 there is a hand-built mock response, not a
version the backend actually rejected. A real optimistic-concurrency bug — the client sending a
version the server does not reject, the retry looping, the reconcile silently dropping the
user's paragraph — is invisible to a mock that was told to answer 409.

So this forces a REAL conflict through the running stack. It types and lets the debounced
autosave settle (the editor now holds the server's current version N). It then makes an
OUT-OF-BAND edit — a direct backend PUT at version N with DIFFERENT content, simulating a second
session — which advances the server to N+1 and leaves the editor's held version stale. Typing
more fires another autosave that PUTs at the now-stale N: the backend answers 409, and the app's
own `saveDocument` refetches N+1 and retries with the editor's content.

The reconcile is then observed live: the saved indicator returns with no error banner (the stale
save was reconciled, not left failed), and reading the document back through the backend shows
the EDITOR's latest text persisted — last-writer-wins (documentApi.ts's stated trade-off), so
the edit survived and was neither lost nor left as the out-of-band content.
"""

import httpx
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from statements.frontend.generation.manual_editor_autosave_statements import (
    ManualEditorAutosaveStatements,
)
from statements.frontend.generation.manual_editor_save_payload_statements import (
    SAVED_STATUS,
    _ACCESS_TOKEN_KEY,
    _REQUEST_TIMEOUT_SECONDS,
    _backend_base_url,
)
from statements.frontend.generation.manual_editor_statements import MANUAL_EDITOR_SELECTOR

SAVE_ERROR_BANNER = (By.CSS_SELECTOR, f"{MANUAL_EDITOR_SELECTOR} [data-testid='me-save-error']")
# The debounce is 1000ms; the reconcile adds a 409 + refetch GET + retry PUT on top of it, so the
# saved indicator can legitimately take longer than a clean autosave. Generous, but not so long
# it hides a reconcile that never completes.
_RECONCILE_WAIT_SECONDS = 20


class ManualEditorConflictReconcileStatements(ManualEditorAutosaveStatements):
    def _resolve_document(self, driver: WebDriver) -> tuple[str, str]:
        """Return (access token, the fresh account's single document id) via the live backend.

        The token is the one the app itself stored in sessionStorage during the live-session
        flow — the same credential the browser's own autosave PUTs carry, so the out-of-band
        edit races the app on genuinely equal footing, not a privileged side channel.
        """
        token = driver.execute_script(
            "return window.sessionStorage.getItem(arguments[0]);", _ACCESS_TOKEN_KEY
        )
        assert token, "expected a live access token in sessionStorage after a live-session flow"
        with self._backend_client(token) as client:
            listing = client.get("/api/v1/documents")
            assert listing.status_code == 200, (
                f"list documents expected 200, got {listing.status_code}: {listing.text}"
            )
            items = listing.json()["items"]
            assert len(items) == 1, (
                f"expected exactly one document for the fresh account, got {len(items)}"
            )
        return token, items[0]["document_id"]

    def _backend_client(self, token: str) -> httpx.Client:
        return httpx.Client(
            base_url=_backend_base_url(),
            timeout=_REQUEST_TIMEOUT_SECONDS,
            headers={"Authorization": f"Bearer {token}"},
        )

    def perform_out_of_band_edit(self, driver: WebDriver, content: str) -> None:
        """Simulate a second session: PUT `content` at the document's CURRENT version.

        Reads the live version first (so the write is accepted, advancing the server past the
        version the editor still holds) and asserts the write landed — a 409 here would mean the
        editor never synced its version and the premise of the test collapsed silently.
        """
        token, document_id = self._resolve_document(driver)
        with self._backend_client(token) as client:
            current = client.get(f"/api/v1/documents/{document_id}")
            assert current.status_code == 200, (
                f"read document expected 200, got {current.status_code}: {current.text}"
            )
            stale_version = current.json()["version"]
            put = client.put(
                f"/api/v1/documents/{document_id}",
                json={"content": content, "version": stale_version},
            )
        assert put.status_code == 200, (
            f"out-of-band edit expected 200 to advance the server version, "
            f"got {put.status_code}: {put.text}"
        )

    def assert_autosave_reconciled_without_error(self, driver: WebDriver) -> None:
        """The stale autosave was reconciled, not left failed: saved returns, no error banner."""
        WebDriverWait(driver, _RECONCILE_WAIT_SECONDS).until(
            ec.visibility_of_element_located(SAVED_STATUS)
        )
        banners = driver.find_elements(*SAVE_ERROR_BANNER)
        assert not banners, (
            f"expected no save-error banner after a reconciled 409, found {len(banners)}"
        )

    def assert_persisted_content_is(self, driver: WebDriver, expected: str) -> None:
        """The persisted content is the EDITOR's latest text — last-writer-wins reconcile.

        Strict equality, not membership: this must fail both if the out-of-band content won (the
        reconcile overwrote the wrong way) and if the editor's edit was lost.
        """
        content = self.read_back_saved_content(driver)
        assert content == expected, (
            f"expected the reconciled content to persist as the editor's text {expected!r}, "
            f"got {content!r}"
        )
