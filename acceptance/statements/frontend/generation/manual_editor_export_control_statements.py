"""Statements for scenario 1.1 — the editor's export control offers a PDF and a DOCX choice.

Given a document open in the editor, opening the export control reveals exactly the two
format choices the export endpoint accepts (`format=pdf|docx`). This drives the real editor
(live session -> createDocument), clicks the export trigger, and asserts each choice is shown
with its own label — a count-only check would lose which formats are offered.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.wait import WebDriverWait

from statements.frontend.base_frontend_statements import WAIT_TIMEOUT_SECONDS
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

# Latency (ms) held on every response while throttled — large enough that the first GET /export
# stays open across the second click, so the in-flight lock is genuinely under test. Mirrors the
# save-queue statements' _SLOW_LATENCY_MS pattern.
_SLOW_LATENCY_MS = 2500


class ExportControlStatements(ManualEditorStatements):
    def open_export_control(self, driver) -> None:
        self._wait_for_visible(driver, EXPORT_TRIGGER).click()

    def throttle_network(self, driver) -> None:
        driver.execute_cdp_cmd("Network.enable", {})
        driver.execute_cdp_cmd(
            "Network.emulateNetworkConditions",
            {
                "offline": False,
                "latency": _SLOW_LATENCY_MS,
                "downloadThroughput": -1,
                "uploadThroughput": -1,
            },
        )

    def clear_network_throttle(self, driver) -> None:
        driver.execute_cdp_cmd(
            "Network.emulateNetworkConditions",
            {"offline": False, "latency": 0, "downloadThroughput": -1, "uploadThroughput": -1},
        )

    def wait_for_export_in_flight(self, driver) -> None:
        """Wait until the PDF option is disabled — the browser-observable proof isExporting is true.

        The control keeps the PDF/DOCX options mounted but sets `disabled`/`aria-disabled` while a
        request is pending (ExportControl.tsx: `disabled={isExporting}`). Waiting on that state is
        what makes the second click PROVABLY land inside the in-flight window, rather than racing a
        fast backend that already released the lock. This does NOT use scenario 3.1's exporting
        indicator — that element does not exist yet.
        """
        WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(
            self._pdf_option_is_disabled,
            "expected the PDF export option to become disabled while its request is in flight",
        )

    @staticmethod
    def _pdf_option_is_disabled(driver: WebDriver) -> bool:
        elements = driver.find_elements(*EXPORT_OPTION_PDF)
        if not elements:
            return False
        option = elements[0]
        return bool(option.get_attribute("disabled")) or (
            option.get_attribute("aria-disabled") == "true"
        )

    def trigger_export_as_pdf_twice(self, driver) -> None:
        """Throttle the network, click the PDF choice, wait for the in-flight lock, then click again.

        The throttle holds the first GET /export open for `_SLOW_LATENCY_MS`, so the second click
        is PROVEN to land while `isExporting` is true (the option disabled). A correct in-flight
        lock drops that second click instead of dispatching a duplicate request; without the lock
        the second click would fire a second GET /export and the count would be 2. The throttle is
        cleared afterward so it never leaks into later assertions.
        """
        self.throttle_network(driver)
        self.open_export_control(driver)
        pdf_option = self._wait_for_visible(driver, EXPORT_OPTION_PDF)
        pdf_option.click()
        self.wait_for_export_in_flight(driver)
        pdf_option.click()
        self.clear_network_throttle(driver)

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
