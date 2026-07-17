import json
import time
from dataclasses import dataclass
from typing import ClassVar
from urllib.parse import urlparse

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

WAIT_TIMEOUT_SECONDS = 5
REQUEST_LOG_SETTLE_SECONDS = 1

# The container each form field (label + input + inline error) is wrapped in.
# Shared across auth pages (both LoginForm.tsx and RegisterForm.tsx render it).
# Proximity assertions resolve it via Element.closest().
FIELD_CONTAINER_CLASS = "auth-field"


@dataclass(frozen=True)
class HintErrorSnapshot:
    """One element's error-display state, compared in a single assertion so a
    failure reports every wrong field at once instead of stopping at the first.
    """

    displayed: bool
    classes: tuple[str, ...]
    text: str

PRIMARY_CTA_BUTTON = (By.CSS_SELECTOR, "[data-testid='header-primary-cta-button']")
TYPE_CARD_DOKLAD = (By.CSS_SELECTOR, "[data-testid='type-card-doklad']")
MODE_CARD_AUTO = (By.CSS_SELECTOR, "[data-testid='mode-card-auto']")


class BaseFrontendStatements:
    """Shared Selenium wait infrastructure for frontend Statements classes."""

    _DEFAULT_PORTS: ClassVar[dict[str, str]] = {"http": "80", "https": "443"}

    @classmethod
    def _normalized_origin(cls, url: str) -> tuple[str, str]:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        port = str(parsed.port) if parsed.port else cls._DEFAULT_PORTS.get(parsed.scheme, "")
        return parsed.scheme, f"{host}:{port}" if port else host

    def _assert_url_path(self, driver: WebDriver, app_url: str, expected_path: str) -> None:
        expected_origin = self._normalized_origin(app_url)

        def is_expected_page(d: WebDriver) -> bool:
            actual = urlparse(d.current_url)
            return (
                self._normalized_origin(d.current_url) == expected_origin
                and actual.path.rstrip("/") == expected_path
            )

        WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(
            is_expected_page, f"expected URL '{app_url}{expected_path}', got '{driver.current_url}'"
        )

    def _wait_for_visible(self, driver: WebDriver, locator: tuple[str, str]) -> WebElement:
        return WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(ec.visibility_of_element_located(locator))

    def _assert_element_text_equals(
        self, driver: WebDriver, locator: tuple[str, str], expected: str, label: str
    ) -> WebElement:
        """Wait for the element, strip its text, and assert exact equality to `expected`."""
        element = self._wait_for_visible(driver, locator)
        actual = element.text.strip()
        assert actual == expected, f"expected {label} to be '{expected}', got '{actual}'"
        return element

    def navigate_to_doklad_type_modal(self, driver: WebDriver, app_url: str) -> None:
        """Navigate to the app, open the primary CTA, and select the 'doklad' type card.

        Shared entry point for both the mode-modal and chat-workspace flows, which
        diverge only in what they click next (a mode card vs. waiting on the modal).
        """
        driver.get(app_url)
        self._wait_for_visible(driver, PRIMARY_CTA_BUTTON).click()
        self._wait_for_visible(driver, TYPE_CARD_DOKLAD).click()
    def _assert_field_visible(
        self,
        driver: WebDriver,
        locator: tuple[str, str],
        expected_type: str,
        expected_placeholder: str,
        label: str,
    ) -> None:
        element = self._wait_for_visible(driver, locator)
        assert element.is_displayed(), f"expected {label} to be visible"
        assert element.get_attribute("type") == expected_type, (
            f"expected {label} type '{expected_type}', got '{element.get_attribute('type')}'"
        )
        assert element.get_attribute("placeholder") == expected_placeholder, (
            f"expected {label} placeholder '{expected_placeholder}', "
            f"got '{element.get_attribute('placeholder')}'"
        )

    def _assert_submit_button_visible(
        self,
        driver: WebDriver,
        locator: tuple[str, str],
        expected_text: str,
        expected_type: str | None = "submit",
    ) -> None:
        element = self._wait_for_visible(driver, locator)
        assert element.is_displayed(), "expected submit button to be visible"
        if expected_type is not None:
            assert element.get_attribute("type") == expected_type, (
                f"expected submit button type '{expected_type}', got '{element.get_attribute('type')}'"
            )
        assert element.text.strip() == expected_text, (
            f"expected submit button text '{expected_text}', got '{element.text}'"
        )

    def _assert_visible(self, driver: WebDriver, locator: tuple[str, str], label: str) -> None:
        element = self._wait_for_visible(driver, locator)
        assert element.is_displayed(), f"expected {label} to be visible"

    def _assert_hint_error_visible(
        self,
        driver: WebDriver,
        locator: tuple[str, str],
        expected_text: str,
        label: str,
        expected_classes: tuple[str, ...],
    ) -> None:
        """Asserts an inline hint-error's full display state in one compare.

        `expected_classes` is the caller's to supply — the hint-error class list
        is page-owned markup, so a shared default here would let a page that
        renders different classes silently assert another page's.
        """
        element = self._wait_for_visible(driver, locator)
        actual = HintErrorSnapshot(
            displayed=element.is_displayed(),
            classes=tuple(element.get_attribute("class").split()),
            text=element.text.strip(),
        )
        expected = HintErrorSnapshot(displayed=True, classes=expected_classes, text=expected_text)
        assert actual == expected, f"expected {label} to be {expected}, got {actual}"

    def _assert_error_shares_field_container_with_input(
        self,
        driver: WebDriver,
        error_locator: tuple[str, str],
        input_locator: tuple[str, str],
        label: str,
    ) -> None:
        """Asserts the error element sits inside the *same* field container as
        its input — i.e. it is rendered next to that field, not as a page-level
        banner that merely carries the same text.

        Proximity is asserted structurally rather than trusted from the error's
        `data-testid` name: a testid is a label the component chooses, so an
        error hoisted to the top of the page would keep passing a testid-only
        check while no longer being "near the field" the spec requires.
        """
        error = self._wait_for_visible(driver, error_locator)
        field_input = self._wait_for_visible(driver, input_locator)
        shares_container = driver.execute_script(
            "const selector = '.' + arguments[2];"
            "const errorField = arguments[0].closest(selector);"
            "return errorField !== null && errorField === arguments[1].closest(selector);",
            error,
            field_input,
            FIELD_CONTAINER_CLASS,
        )
        assert shares_container, (
            f"expected {label} to render inside the same .{FIELD_CONTAINER_CLASS} container "
            f"as its input {input_locator[1]}, but it did not"
        )

    def _assert_disabled(self, driver: WebDriver, locator: tuple[str, str], label: str) -> None:
        element = self._wait_for_visible(driver, locator)
        try:
            WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(lambda _: not element.is_enabled())
        except TimeoutException:
            pass
        assert not element.is_enabled(), f"expected {label} to be disabled"

    def _count_requests_to(self, driver: WebDriver, path_substring: str, method: str = "POST") -> int:
        """Counts Network.requestWillBeSent CDP events whose URL contains
        `path_substring` and whose HTTP method matches `method` (default
        "POST" — excludes CORS preflight OPTIONS requests to the same URL).
        Requires the webdriver fixture to enable
        `goog:loggingPrefs: {"performance": "ALL"}`. Sleeps briefly first
        since CDP log delivery is asynchronous relative to the triggering
        click.
        """
        time.sleep(REQUEST_LOG_SETTLE_SECONDS)

        count = 0
        for entry in driver.get_log("performance"):
            message = json.loads(entry["message"])["message"]
            if message.get("method") != "Network.requestWillBeSent":
                continue
            request = message.get("params", {}).get("request", {})
            url = request.get("url", "")
            if path_substring in url and request.get("method") == method:
                count += 1
        return count
