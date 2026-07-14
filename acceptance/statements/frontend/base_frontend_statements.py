from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

WAIT_TIMEOUT_SECONDS = 5

PRIMARY_CTA_BUTTON = (By.CSS_SELECTOR, "[data-testid='header-primary-cta-button']")
TYPE_CARD_DOKLAD = (By.CSS_SELECTOR, "[data-testid='type-card-doklad']")
MODE_CARD_AUTO = (By.CSS_SELECTOR, "[data-testid='mode-card-auto']")


class BaseFrontendStatements:
    """Shared Selenium wait infrastructure for frontend Statements classes."""

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
