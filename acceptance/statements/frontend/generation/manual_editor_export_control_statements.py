"""Statements for scenario 1.1 — the editor's export control offers a PDF and a DOCX choice.

Given a document open in the editor, opening the export control reveals exactly the two
format choices the export endpoint accepts (`format=pdf|docx`). This drives the real editor
(live session -> createDocument), clicks the export trigger, and asserts each choice is shown
with its own label — a count-only check would lose which formats are offered.
"""

from selenium.webdriver.common.by import By

from statements.frontend.generation.manual_editor_statements import (
    MANUAL_EDITOR_SELECTOR,
    ManualEditorStatements,
)

EXPORT_TRIGGER = (
    By.CSS_SELECTOR, f"{MANUAL_EDITOR_SELECTOR} [data-testid='export-control-trigger']"
)
EXPORT_OPTION_PDF = (
    By.CSS_SELECTOR, f"{MANUAL_EDITOR_SELECTOR} [data-testid='export-option-pdf']"
)
EXPORT_OPTION_DOCX = (
    By.CSS_SELECTOR, f"{MANUAL_EDITOR_SELECTOR} [data-testid='export-option-docx']"
)

EXPECTED_PDF_LABEL = "PDF"
EXPECTED_DOCX_LABEL = "DOCX"

# The export endpoint is GET /api/v1/documents/{id}/export?format=pdf|docx, so every export
# request URL contains this path segment. Counting Network.requestWillBeSent GET events to it
# (via the perf-log helper) is the browser-observable proof of "only one request is sent" — a
# disabled/aria-busy state check would only prove the presentation, not that no second request
# actually left the browser.
EXPORT_REQUEST_PATH = "/export"


class ExportControlStatements(ManualEditorStatements):
    def open_export_control(self, driver) -> None:
        self._wait_for_visible(driver, EXPORT_TRIGGER).click()

    def trigger_export_as_pdf_twice(self, driver) -> None:
        """Open the export control and click the PDF choice twice in immediate succession.

        The second click lands before the first export request returns — the in-flight window
        scenario 2.1 guards. Both clicks target the same mounted option element, so a correct
        in-flight lock (the option disabled while its request is open) simply drops the second
        click instead of dispatching a duplicate request.
        """
        self.open_export_control(driver)
        pdf_option = self._wait_for_visible(driver, EXPORT_OPTION_PDF)
        pdf_option.click()
        pdf_option.click()

    def assert_exactly_one_export_request_was_sent(self, driver) -> None:
        request_count = self._count_requests_to(driver, EXPORT_REQUEST_PATH, method="GET")
        assert request_count == 1, (
            f"expected exactly one export request to '{EXPORT_REQUEST_PATH}' to be sent "
            f"(the in-flight lock drops the second click), got {request_count}"
        )

    def assert_pdf_and_docx_choices_are_shown(self, driver) -> None:
        self._assert_choice_shown(driver, EXPORT_OPTION_PDF, EXPECTED_PDF_LABEL)
        self._assert_choice_shown(driver, EXPORT_OPTION_DOCX, EXPECTED_DOCX_LABEL)

    def _assert_choice_shown(self, driver, locator, expected_label: str) -> None:
        choice = self._wait_for_visible(driver, locator)
        actual = choice.text.strip()
        # The choice label is a value the test defines (determinism category 1), so pin it
        # exactly — a button reading "Скачать PDF" or "PDF ▾" must not pass. The frontend
        # renders exactly this text; the green phase matches the test, not the reverse.
        assert actual == expected_label, (
            f"expected the {expected_label} export choice to show exactly "
            f"'{expected_label}', got '{actual}'"
        )
