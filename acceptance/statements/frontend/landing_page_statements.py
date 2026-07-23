from typing import ClassVar

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from statements.frontend.base_frontend_statements import BaseFrontendStatements

HERO_HEADING = (By.CSS_SELECTOR, "[data-testid='hero-heading']")
# The hero CTA was removed during the 2026-07-10 Figma-alignment pass; the header nav
# CTA (data-testid="header-primary-cta-button" in Header.tsx) is now the only primary CTA.
PRIMARY_CTA_BUTTON = (By.CSS_SELECTOR, "[data-testid='header-primary-cta-button']")


class LandingPageStatements(BaseFrontendStatements):
    # Copy is authoritative from the Figma file "Labs-2026 ООО ИИ", frame `Desktop`
    # (node 90:880), which takes precedence over the older Claude-generated HTML mockup for
    # the Landing screen per ProductSpecification/stories/01-auto-generate-doklad/tests/
    # 02_UI_Tests.md. The heading renders as two spans; `.text` flattens them to one line.
    EXPECTED_HERO_HEADING_TEXT: ClassVar[str] = "Textery — самая быстрая нейросеть для докладов"
    EXPECTED_PRIMARY_CTA_TEXT: ClassVar[str] = "Создать генерацию"

    def navigate_to_landing_page(self, driver: WebDriver, app_url: str) -> None:
        driver.get(app_url)

    def assert_hero_heading_is_visible(self, driver: WebDriver) -> None:
        self._assert_element_visible_with_text(
            driver, HERO_HEADING, self.EXPECTED_HERO_HEADING_TEXT, "hero heading"
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
