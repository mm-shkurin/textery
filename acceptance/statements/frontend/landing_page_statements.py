from typing import ClassVar

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

HERO_HEADING = (By.CSS_SELECTOR, "[data-testid='hero-heading']")
HERO_SUBHEADING = (By.CSS_SELECTOR, "[data-testid='hero-subheading']")
# Scoped to "hero-primary-cta-button", not a generic "primary-cta-button": the Figma
# export (.memory-bank/figma/Landing.png) shows three "Создать генерацию" buttons
# (header nav, hero, page footer) — a shared, unscoped testid would let Selenium's
# first-DOM-match resolution silently bind to the wrong one once green-frontend wires
# up all three instances.
PRIMARY_CTA_BUTTON = (By.CSS_SELECTOR, "[data-testid='hero-primary-cta-button']")

WAIT_TIMEOUT_SECONDS = 5


class LandingPageStatements:
    # Copy is authoritative from the Figma export (.memory-bank/figma/Landing.png), which
    # takes precedence over the older Claude-generated HTML mockup for the Landing screen
    # per ProductSpecification/stories/01-auto-generate-doklad/tests/02_UI_Tests.md.
    EXPECTED_HERO_HEADING_TEXT: ClassVar[str] = "Word онлайн"
    EXPECTED_HERO_SUBHEADING_TEXT: ClassVar[str] = "С возможностью генерации через нейросеть Textery AI"
    EXPECTED_PRIMARY_CTA_TEXT: ClassVar[str] = "Создать генерацию"

    def navigate_to_landing_page(self, driver: WebDriver, app_url: str) -> None:
        driver.get(app_url)

    def assert_hero_heading_is_visible(self, driver: WebDriver) -> None:
        self._assert_element_visible_with_text(
            driver, HERO_HEADING, self.EXPECTED_HERO_HEADING_TEXT, "hero heading"
        )

    def assert_hero_subheading_is_visible(self, driver: WebDriver) -> None:
        self._assert_element_visible_with_text(
            driver, HERO_SUBHEADING, self.EXPECTED_HERO_SUBHEADING_TEXT, "hero subheading"
        )

    def assert_primary_cta_button_is_visible(self, driver: WebDriver) -> None:
        self._assert_element_visible_with_text(
            driver, PRIMARY_CTA_BUTTON, self.EXPECTED_PRIMARY_CTA_TEXT, "primary CTA button"
        )

    def _assert_element_visible_with_text(
        self, driver: WebDriver, locator: tuple[str, str], expected_text: str, label: str
    ) -> None:
        element = self._wait_for_visible(driver, locator)
        assert element.is_displayed(), f"expected {label} to be visible"
        assert element.text.strip() == expected_text, (
            f"expected {label} text '{expected_text}', got '{element.text}'"
        )

    def _wait_for_visible(self, driver: WebDriver, locator: tuple[str, str]) -> WebElement:
        return WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(ec.visibility_of_element_located(locator))
