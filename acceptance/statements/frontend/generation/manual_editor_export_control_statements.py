"""Statements for scenario 1.1 — the editor's export control offers a PDF and a DOCX choice.

Given a document open in the editor, opening the export control reveals exactly the two
format choices the export endpoint accepts (`format=pdf|docx`). This drives the real editor
(live session -> createDocument), clicks the export trigger, and asserts each choice is shown
with its own label — a count-only check would lose which formats are offered.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from statements.frontend.base_frontend_statements import WAIT_TIMEOUT_SECONDS
from statements.frontend.network_throttle_mixin import NetworkThrottleMixin
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
# Scenario 3.1: a VISIBLE exporting indicator shown while a request is in flight. This is the
# `save-spinner` precedent (manual_editor_save_queue_statements.py) applied to export — a
# distinct element from scenario 2.1's `disabled`/`aria-disabled` option state, which proves the
# lock but is not a progress indicator the user can see. This element does not exist yet; the
# green phase renders it inside the control while `isExporting` is true.
EXPORT_SPINNER = (
    By.CSS_SELECTOR, f"{MANUAL_EDITOR_SELECTOR} [data-testid='export-spinner']"
)

EXPECTED_PDF_LABEL = "PDF"
EXPECTED_DOCX_LABEL = "DOCX"

# The export endpoint is GET /api/v1/documents/{id}/export?format=pdf|docx, so every export
# request URL contains this path segment. Counting Network.requestWillBeSent GET events to it
# (via the perf-log helper) is the browser-observable proof of "only one request is sent" — a
# disabled/aria-busy state check would only prove the presentation, not that no second request
# actually left the browser.
EXPORT_REQUEST_PATH = "/export"


class ExportControlStatements(NetworkThrottleMixin, ManualEditorStatements):
    def open_export_control(self, driver) -> None:
        self._wait_for_visible(driver, EXPORT_TRIGGER).click()

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

    def _open_throttle_and_click_pdf(self, driver):
        """Open the export control, throttle the network, click PDF once; return the option.

        Shared ordering scenario 2.1's fix established: opening the export control is a local
        toggle that sends no network request, so it must happen BEFORE throttling — under the CDP
        throttle the trigger/option would never become visible within the wait and the test would
        time out on the menu-open (as scenario 1.1, which does not throttle, proves). The GET
        /export fires only on the PDF-option click, so the throttle only needs to be active from
        that click onward, and it holds that first GET /export open for `SLOW_LATENCY_MS`. The
        caller decides what to do with the in-flight request and when to clear the throttle.
        """
        self.open_export_control(driver)
        pdf_option = self._wait_for_visible(driver, EXPORT_OPTION_PDF)
        self.throttle_network(driver)
        pdf_option.click()
        return pdf_option

    def trigger_export_as_pdf_twice(self, driver) -> None:
        """Trigger a throttled PDF export, wait for the in-flight lock, then click PDF again.

        The throttle holds the first GET /export open for `SLOW_LATENCY_MS`, so the second click
        is PROVEN to land while `isExporting` is true (the option disabled). A correct in-flight
        lock drops that second click instead of dispatching a duplicate request; without the lock
        the second click would fire a second GET /export and the count would be 2. The throttle is
        cleared afterward so it never leaks into later assertions.
        """
        pdf_option = self._open_throttle_and_click_pdf(driver)
        self.wait_for_export_in_flight(driver)
        pdf_option.click()
        self.clear_network_throttle(driver)

    def assert_exactly_one_export_request_was_sent(self, driver) -> None:
        request_count = self._count_requests_to(driver, EXPORT_REQUEST_PATH, method="GET")
        assert request_count == 1, (
            f"expected exactly one export request to '{EXPORT_REQUEST_PATH}' to be sent "
            f"(the in-flight lock drops the second click), got {request_count}"
        )

    def trigger_throttled_pdf_export(self, driver) -> None:
        """Trigger a single throttled PDF export and leave it in flight (throttle NOT cleared here).

        Unlike scenario 2.1 this clicks ONCE and does NOT clear the throttle: the request stays in
        flight so the caller can assert the exporting indicator is shown WHILE `isExporting` is
        true. `assert_exporting_indicator_is_shown` clears the throttle after observing the
        indicator.
        """
        self._open_throttle_and_click_pdf(driver)

    def assert_exporting_indicator_is_shown(self, driver) -> None:
        """Assert the visible exporting indicator appears while the export request is in flight.

        Waits (strict — element must become visible, not a sleep) on the `export-spinner` testid,
        then asserts it is displayed. This is a DIFFERENT element from scenario 2.1's disabled
        option: 2.1 proved no second request leaves the browser; 3.1 proves the user SEES progress
        while the file is generated. The throttle is cleared last so it never leaks into any later
        assertion (the driver is function-scoped, but releasing explicitly keeps the intent clear).
        """
        spinner = WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(
            ec.visibility_of_element_located(EXPORT_SPINNER),
            "expected the exporting indicator to be shown while the export request is in flight",
        )
        assert spinner.is_displayed(), (
            "expected the exporting indicator to be visible while the export is in flight"
        )
        self.clear_network_throttle(driver)

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
