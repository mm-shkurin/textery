from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

WAIT_TIMEOUT_SECONDS = 5


class BaseFrontendStatements:
    """Shared Selenium wait infrastructure for frontend Statements classes."""

    def _wait_for_visible(self, driver: WebDriver, locator: tuple[str, str]) -> WebElement:
        return WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(ec.visibility_of_element_located(locator))

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
    ) -> None:
        element = self._wait_for_visible(driver, locator)
        assert element.is_displayed(), "expected submit button to be visible"
        assert element.get_attribute("type") == "submit", (
            f"expected submit button type 'submit', got '{element.get_attribute('type')}'"
        )
        assert element.text.strip() == expected_text, (
            f"expected submit button text '{expected_text}', got '{element.text}'"
        )

    def _assert_disabled(self, driver: WebDriver, locator: tuple[str, str], label: str) -> None:
        element = self._wait_for_visible(driver, locator)
        assert not element.is_enabled(), f"expected {label} to be disabled"

    def _count_requests_to(self, driver: WebDriver, path_substring: str) -> int:
        """Counts Network.requestWillBeSent CDP events whose URL contains
        `path_substring`. Requires the webdriver fixture to enable
        `goog:loggingPrefs: {"performance": "ALL"}`.
        """
        import json

        count = 0
        for entry in driver.get_log("performance"):
            message = json.loads(entry["message"])["message"]
            if message.get("method") != "Network.requestWillBeSent":
                continue
            url = message.get("params", {}).get("request", {}).get("url", "")
            if path_substring in url:
                count += 1
        return count
