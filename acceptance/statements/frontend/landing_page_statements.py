from typing import ClassVar

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

HERO_HEADING = (By.CSS_SELECTOR, "[data-testid='hero-heading']")
HERO_SUBHEADING = (By.CSS_SELECTOR, "[data-testid='hero-subheading']")
PRIMARY_CTA_BUTTON = (By.CSS_SELECTOR, "[data-testid='primary-cta-button']")

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
        element = self._wait_for_visible(driver, HERO_HEADING)
        assert element.is_displayed(), "expected hero heading to be visible"
        assert element.text.strip() == self.EXPECTED_HERO_HEADING_TEXT, (
            f"expected hero heading text '{self.EXPECTED_HERO_HEADING_TEXT}', got '{element.text}'"
        )

    def assert_hero_subheading_is_visible(self, driver: WebDriver) -> None:
        element = self._wait_for_visible(driver, HERO_SUBHEADING)
        assert element.is_displayed(), "expected hero subheading to be visible"
        assert element.text.strip() == self.EXPECTED_HERO_SUBHEADING_TEXT, (
            f"expected hero subheading text '{self.EXPECTED_HERO_SUBHEADING_TEXT}', got '{element.text}'"
        )

    def assert_primary_cta_button_is_visible(self, driver: WebDriver) -> None:
        element = self._wait_for_visible(driver, PRIMARY_CTA_BUTTON)
        assert element.is_displayed(), "expected primary CTA button to be visible"
        assert element.text.strip() == self.EXPECTED_PRIMARY_CTA_TEXT, (
            f"expected CTA button text '{self.EXPECTED_PRIMARY_CTA_TEXT}', got '{element.text}'"
        )

    def _wait_for_visible(self, driver: WebDriver, locator: tuple[str, str]) -> WebElement:
        return WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(ec.visibility_of_element_located(locator))
