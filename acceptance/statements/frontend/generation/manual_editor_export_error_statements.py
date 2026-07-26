"""Statements for scenario 3.2 — a failed export shows an inline error with retry, doc unchanged.

Split out of manual_editor_export_control_statements.py to keep both files under the 200-line
limit. `ExportErrorStatementsMixin` is mixed into `ExportControlStatements`, so the same
`export_control_statements` fixture exposes these helpers.

The failure lever is a CDP URL block on the export GET (`Network.setBlockedURLs`): the request
leaves the browser and fails deterministically (net::ERR_BLOCKED_BY_CLIENT), mirroring how the
throttle mixin holds a request open. This is the "request fails" of the scenario — the prod UI
today swallows that rejection (ExportControl.tsx `.catch(() => {})`) and renders no error, so the
visibility wait on `export-error` is what makes RED fail until the green phase surfaces it.
"""

from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from statements.frontend.base_frontend_statements import WAIT_TIMEOUT_SECONDS
from statements.frontend.generation.export_control_locators import EXPORT_OPTION_PDF
from statements.frontend.generation.manual_editor_statements import (
    EDITABLE_CONTENT,
    MANUAL_EDITOR,
    MANUAL_EDITOR_SELECTOR,
)
from selenium.webdriver.common.by import By

# Scenario 3.2 introduces two elements the control does not render yet: an inline error message
# and a retry affordance beside it. `export-error` is the user-visible failure notice;
# `export-retry` is the button that re-dispatches the export. Both are asserted by strict
# visibility (must appear), not presence — a hidden error node would not satisfy "is shown".
EXPORT_ERROR = (
    By.CSS_SELECTOR, f"{MANUAL_EDITOR_SELECTOR} [data-testid='export-error']"
)
EXPORT_RETRY = (
    By.CSS_SELECTOR, f"{MANUAL_EDITOR_SELECTOR} [data-testid='export-retry']"
)

# Chrome DevTools URL-block pattern. The export endpoint is
# GET /api/v1/documents/{id}/export?format=pdf, so `*/export*` matches the path segment plus its
# query. Blocking it makes the in-flight GET fail rather than resolve, which is the browser-
# observable "the request fails" the scenario needs.
EXPORT_BLOCK_PATTERN = "*/export*"

# The failure notice and retry label are values the TEST defines (determinism category 1), so they
# are pinned exactly — visibility alone would pass a blank node or the wrong message. The error text
# is the string the export transport already throws (documentApi.ts exportDocument: 'Не удалось
# экспортировать документ'); the retry affordance carries the existing editor "retry" accessible
# name ('Повторить', editorToolbarActions.ts). The green phase must render exactly these; the test
# is the specification, not the reverse.
EXPECTED_EXPORT_ERROR_MESSAGE = "Не удалось экспортировать документ"
EXPECTED_RETRY_LABEL = "Повторить"


class ExportErrorStatementsMixin:
    """3.2 helpers: fail an export, assert the inline error + retry, assert the doc is unchanged."""

    def block_export_requests(self, driver) -> None:
        driver.execute_cdp_cmd("Network.enable", {})
        driver.execute_cdp_cmd("Network.setBlockedURLs", {"urls": [EXPORT_BLOCK_PATTERN]})

    def unblock_export_requests(self, driver) -> None:
        driver.execute_cdp_cmd("Network.setBlockedURLs", {"urls": []})

    def trigger_failed_pdf_export(self, driver) -> None:
        """Open the export control, block the export GET, click PDF so the request fails.

        Ordering mirrors the throttle scenarios: opening the control is a local toggle that sends
        no request, so it happens BEFORE the block (a block active during menu-open would not stop
        the option appearing, but keeping the sequence identical to 2.1/3.1 avoids surprises). The
        GET /export fires only on the PDF click, and the block makes exactly that request fail.
        """
        self.open_export_control(driver)
        pdf_option = self._wait_for_visible(driver, EXPORT_OPTION_PDF)
        # Capture the editable content BEFORE the failure so the "document unchanged" clause can
        # compare against a real baseline. Snapshotting after the control opens (a local toggle
        # that sends no request) but before the blocked GET fires means any content the failed
        # export blanks or mutates would diverge from this text.
        self._document_content_baseline = self._wait_for_visible(
            driver, EDITABLE_CONTENT
        ).text
        self.block_export_requests(driver)
        pdf_option.click()

    def assert_export_error_with_retry_is_shown(self, driver) -> None:
        """Assert an inline export error appears with a retry affordance after the request fails.

        Strict visibility waits (element must become visible, not a sleep) on `export-error` and
        `export-retry`. Today the control swallows the rejection and renders neither, so this wait
        times out — the RED failure. The block is cleared last so it never leaks into a later
        assertion (the driver is function-scoped, but releasing explicitly keeps the intent clear).
        """
        error = WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(
            ec.visibility_of_element_located(EXPORT_ERROR),
            "expected an inline export error to be shown after the export request fails",
        )
        actual_error = error.text.strip()
        assert actual_error == EXPECTED_EXPORT_ERROR_MESSAGE, (
            f"expected the inline export error to read exactly "
            f"'{EXPECTED_EXPORT_ERROR_MESSAGE}', got '{actual_error}'"
        )
        retry = WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(
            ec.visibility_of_element_located(EXPORT_RETRY),
            "expected a retry affordance to be shown beside the export error",
        )
        actual_retry = (retry.text.strip() or retry.get_attribute("aria-label") or "").strip()
        assert actual_retry == EXPECTED_RETRY_LABEL, (
            f"expected the export retry affordance to read exactly "
            f"'{EXPECTED_RETRY_LABEL}', got '{actual_retry}'"
        )
        self.unblock_export_requests(driver)

    def assert_document_view_is_unchanged(self, driver) -> None:
        """Assert the editor view is intact after a failed export — no navigation, content present.

        "The document view is unchanged" means the failed export did not tear down or navigate
        away from the editor: the manual editor shell is still displayed and its editable content
        area is still mounted and visible. A failure that redirected, blanked the editor, or
        unmounted the content area would leave these absent and this assertion would fail.
        """
        editor = self._wait_for_visible(driver, MANUAL_EDITOR)
        assert editor.is_displayed(), (
            "expected the manual editor to remain displayed after a failed export"
        )
        content = self._wait_for_visible(driver, EDITABLE_CONTENT)
        assert content.is_displayed(), (
            "expected the editable content area to remain visible after a failed export"
        )
        # "Unchanged" means the content is intact, not merely still mounted — a failed export that
        # blanked or mutated the editable area would still be visible but would fail this equality.
        actual_content = content.text
        assert actual_content == self._document_content_baseline, (
            "expected the document content to be unchanged after a failed export, but it changed "
            f"from '{self._document_content_baseline}' to '{actual_content}'"
        )
