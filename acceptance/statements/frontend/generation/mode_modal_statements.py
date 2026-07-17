from typing import ClassVar

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from statements.frontend.base_frontend_statements import BaseFrontendStatements, MODE_CARD_AUTO

MODE_MODAL = (By.CSS_SELECTOR, "[data-testid='mode-modal']")
MODE_CARD_MANUAL = (By.CSS_SELECTOR, "[data-testid='mode-card-manual']")
MODE_NAME_MANUAL = (By.CSS_SELECTOR, "[data-testid='mode-card-manual'] .mode-name")
MODE_NAME_AUTO = (By.CSS_SELECTOR, "[data-testid='mode-card-auto'] .mode-name")
SOON_BADGE = (By.CSS_SELECTOR, ".soon-pill")

# Available (non-disabled) SelectableCard renders exactly this class, with no
# " disabled" suffix -- see SelectableCard.tsx: `${cardClassName}${available ? '' : ' disabled'}`.
EXPECTED_AVAILABLE_CARD_CLASS = "mode-card"


class ModeModalStatements(BaseFrontendStatements):
    # Copy pulled from the actual built component
    # (frontend/src/features/generation/components/ModeModal.tsx `MODES`).
    EXPECTED_MANUAL_MODE_NAME: ClassVar[str] = "Ручной режим"
    EXPECTED_AUTO_MODE_NAME: ClassVar[str] = "Автоматический режим"

    def navigate_to_mode_modal(self, driver: WebDriver, app_url: str) -> None:
        self.navigate_to_doklad_type_modal(driver, app_url)
        self._wait_for_visible(driver, MODE_MODAL)

    def assert_manual_mode_card_is_available_and_selectable(self, driver: WebDriver) -> None:
        self._assert_card_is_available_and_selectable(
            driver, MODE_CARD_MANUAL, MODE_NAME_MANUAL, self.EXPECTED_MANUAL_MODE_NAME, "manual mode card"
        )

    def assert_auto_mode_card_is_available_and_selectable(self, driver: WebDriver) -> None:
        self._assert_card_is_available_and_selectable(
            driver, MODE_CARD_AUTO, MODE_NAME_AUTO, self.EXPECTED_AUTO_MODE_NAME, "auto mode card"
        )

    def assert_no_card_shows_soon_badge(self, driver: WebDriver) -> None:
        badges = driver.find_elements(*SOON_BADGE)
        assert len(badges) == 0, (
            f"expected no 'скоро' badge in the mode modal, found {len(badges)}"
        )

    def _assert_card_is_available_and_selectable(
        self,
        driver: WebDriver,
        card_locator: tuple[str, str],
        name_locator: tuple[str, str],
        expected_name: str,
        label: str,
    ) -> None:
        card = self._wait_for_visible(driver, card_locator)
        self._assert_card_class_marks_it_available(card, label)
        assert card.is_enabled() is True, f"expected {label} to be enabled/selectable, was disabled"

        self._assert_element_text_equals(driver, name_locator, expected_name, f"{label} name")

    def _assert_card_class_marks_it_available(self, card: WebElement, label: str) -> None:
        actual_class = card.get_attribute("class")
        assert actual_class == EXPECTED_AVAILABLE_CARD_CLASS, (
            f"expected {label} class to be exactly '{EXPECTED_AVAILABLE_CARD_CLASS}' "
            f"(no 'disabled' suffix), got '{actual_class}'"
        )
