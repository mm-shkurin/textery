"""Statements for scenario 4.2 — an out-of-order save never leaves stale content displayed.

The jsdom test hand-drove the queue with fake promises; it never exercised the queue through a
real click while a real PUT was in flight. This throttles the network so the first save stays
in flight long enough to type more and click Save again (which the design queues), then reads
the backend back to prove the LATEST edit won — the displayed "Сохранено" reflects the newest
content, never a stale earlier save.
"""

import json

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from statements.frontend.base_frontend_statements import WAIT_TIMEOUT_SECONDS
from statements.frontend.generation.manual_editor_save_payload_statements import (
    ManualEditorSavePayloadStatements,
    SAVE_BUTTON,
    SAVED_STATUS,
)
from statements.frontend.generation.manual_editor_statements import (
    EDITABLE_CONTENT,
    MANUAL_EDITOR_SELECTOR,
)

SAVE_SPINNER = (By.CSS_SELECTOR, f"{MANUAL_EDITOR_SELECTOR} [data-testid='save-spinner']")

# Enough latency that a human-speed type + click lands while the first PUT is still open.
_SLOW_LATENCY_MS = 2500


class ManualEditorSaveQueueStatements(ManualEditorSavePayloadStatements):
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

    def click_save(self, driver) -> None:
        self._wait_for_visible(driver, SAVE_BUTTON).click()

    def wait_for_save_in_flight(self, driver) -> None:
        # The spinner renders while isSaving is true — proof the first PUT is genuinely open, so
        # the second click really does land during the in-flight window (not after it settled).
        WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(
            ec.visibility_of_element_located(SAVE_SPINNER)
        )

    def wait_for_saved(self, driver) -> None:
        WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(
            ec.visibility_of_element_located(SAVED_STATUS)
        )

    def type_more_in_editor(self, driver, text: str) -> None:
        # Append at the current caret without re-clicking (which would move the caret).
        self._wait_for_visible(driver, EDITABLE_CONTENT).send_keys(text)

    def assert_saved_content_is(self, driver, expected: str) -> None:
        content = self.read_back_saved_content(driver)
        assert content == expected, (
            f"expected the LATEST edit {expected!r} to win the save round-trip (never a stale "
            f"earlier save), got {content!r}"
        )

    def assert_exactly_two_document_puts(self, driver) -> None:
        """Count the PUT /documents/{id} requests over the run — must be exactly two.

        The initial save is one; the mid-flight edit queues exactly one re-save (consumed in the
        first save's `.then`), so two total. This is the concrete proof the queue behaved: ONE
        rules out a dropped queue (the re-save never fired), and TWO rules out the design
        regressing to fire concurrent PUTs (three+ near-simultaneous requests) — the version-race
        the strictly-sequential queue exists to prevent. The perf log is enabled on the driver
        fixture (`goog:loggingPrefs performance`).
        """
        puts = 0
        for entry in driver.get_log("performance"):
            message = json.loads(entry["message"])["message"]
            if message.get("method") != "Network.requestWillBeSent":
                continue
            request = message.get("params", {}).get("request", {})
            if request.get("method") == "PUT" and "/api/v1/documents/" in request.get("url", ""):
                puts += 1
        assert puts == 2, (
            f"expected exactly two PUT /documents saves (initial + one queued re-save), got {puts}"
        )
