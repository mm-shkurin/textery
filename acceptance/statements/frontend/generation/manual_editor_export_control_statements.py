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


class ExportControlStatements(ManualEditorStatements):
    def open_export_control(self, driver) -> None:
        self._wait_for_visible(driver, EXPORT_TRIGGER).click()

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
