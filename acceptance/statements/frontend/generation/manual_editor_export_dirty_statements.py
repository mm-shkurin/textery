"""Statements for scenario 4.1 — exporting with unsaved edits saves FIRST.

Design decision (SAVE-FIRST branch of the spec, 17_ExportDocument_Notes.md): export renders the
*stored* HTML, so unsaved editor edits would produce a silently stale file. When the user triggers
an export while the editor is dirty, the app saves first (PUT /api/v1/documents/{id}) and only after
that save completes does the export request (GET /api/v1/documents/{id}/export?format=pdf) fire.

Split out of manual_editor_export_control_statements.py to keep both files under the 200-line
limit. `ExportDirtyStatementsMixin` is mixed into `ExportControlStatements`, so the same
`export_control_statements` fixture exposes these helpers. Ordering is proven from the CDP
performance log (enabled on the webdriver fixture via `goog:loggingPrefs performance`): a
save PUT must appear BEFORE the first export GET — presence alone is not enough, the positions
are compared strictly.
"""

import json
import time

from statements.frontend.base_frontend_statements import WAIT_TIMEOUT_SECONDS
from statements.frontend.generation.export_control_locators import EXPORT_OPTION_PDF
from statements.frontend.generation.manual_editor_statements import EDITABLE_CONTENT

# The edit that dirties the document before the export is triggered. Any unsent keystroke makes
# the editor's in-memory content diverge from the stored HTML, which is exactly the "unsaved
# edits" precondition the scenario needs — a stored-only export would then be stale.
EXPORT_DIRTY_EDIT_TEXT = "Черновик, ещё не сохранён"

# The save endpoint is PUT /api/v1/documents/{id}; the export endpoint is
# GET /api/v1/documents/{id}/export?format=pdf. Both live under this path prefix, so the method
# (PUT vs GET) plus the `/export` segment tell a save apart from an export in the request log.
DOCUMENT_PATH = "/api/v1/documents/"
EXPORT_PATH = "/export"

# CDP log delivery lags the triggering click, and the export GET only fires AFTER the save PUT
# resolves, so the two requests arrive in separate log drains. Poll-and-accumulate until the
# export GET is seen (get_log drains the buffer, so a single read would miss the earlier PUT).
_POLL_INTERVAL_SECONDS = 0.25


class ExportDirtyStatementsMixin:
    """4.1 helpers: dirty the editor, trigger a PDF export, assert the save precedes the export."""

    def make_unsaved_edit(self, driver) -> None:
        """Type into the editor so its content diverges from the stored HTML (unsaved edits)."""
        editable = self._wait_for_visible(driver, EDITABLE_CONTENT)
        editable.click()
        editable.send_keys(EXPORT_DIRTY_EDIT_TEXT)

    def trigger_pdf_export_with_unsaved_edits(self, driver) -> None:
        """Open the export control and click PDF while the editor holds unsaved edits.

        No network throttle here: unlike the in-flight scenarios we WANT both the save PUT and the
        export GET to complete so the performance log captures their real ordering. Opening the
        control is a local toggle (no request); the GET /export fires only on this PDF click, and
        under the save-first design a PUT /documents/{id} must precede it.
        """
        self.open_export_control(driver)
        self._wait_for_visible(driver, EXPORT_OPTION_PDF).click()

    def assert_export_saves_before_exporting(self, driver) -> None:
        """Assert a save PUT is sent and the export GET fires strictly AFTER it.

        Presence is not enough — the whole point of save-first is ordering, so the first save PUT
        must occupy an earlier position in the request stream than the first export GET. Today
        ExportControl receives only `documentId` (no dirty flag, no `save`), so the click fires the
        export GET with NO preceding PUT: `save_index` is None and the first assertion fails.
        """
        requests = self._collect_document_requests_until_export(driver)
        save_index = self._first_index(requests, method="PUT", must_be_export=False)
        assert save_index is not None, (
            "expected a save (PUT /api/v1/documents/{id}) to be sent before the export when the "
            f"editor has unsaved edits, but no save request was observed in {requests}"
        )
        export_index = self._first_index(requests, method="GET", must_be_export=True)
        assert export_index is not None, (
            f"expected an export request (GET .../export) to be sent, but none was in {requests}"
        )
        assert save_index < export_index, (
            "expected the save PUT to be sent BEFORE the export GET (save-first), but the export "
            f"fired at position {export_index} and the save at {save_index} in {requests}"
        )

    def _collect_document_requests_until_export(self, driver) -> list[tuple[str, str]]:
        """Poll the CDP performance log, accumulating document (method, url) pairs in order.

        get_log drains the buffer, so requests arriving in different drains (the save PUT, then the
        export GET after it resolves) are appended across polls to preserve chronological order.
        Stops once an export GET is seen, or after the shared wait timeout.
        """
        requests: list[tuple[str, str]] = []
        deadline = time.monotonic() + WAIT_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            requests.extend(self._drain_document_requests(driver))
            if self._first_index(requests, method="GET", must_be_export=True) is not None:
                return requests
            time.sleep(_POLL_INTERVAL_SECONDS)
        return requests

    @staticmethod
    def _drain_document_requests(driver) -> list[tuple[str, str]]:
        drained: list[tuple[str, str]] = []
        for entry in driver.get_log("performance"):
            message = json.loads(entry["message"])["message"]
            if message.get("method") != "Network.requestWillBeSent":
                continue
            request = message.get("params", {}).get("request", {})
            url = request.get("url", "")
            if DOCUMENT_PATH in url:
                drained.append((request.get("method", ""), url))
        return drained

    @staticmethod
    def _first_index(
        requests: list[tuple[str, str]], method: str, must_be_export: bool
    ) -> int | None:
        for index, (request_method, url) in enumerate(requests):
            if request_method != method:
                continue
            if (EXPORT_PATH in url) == must_be_export:
                return index
        return None
