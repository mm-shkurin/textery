from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from statements.frontend.base_frontend_statements import BaseFrontendStatements, WAIT_TIMEOUT_SECONDS

MODE_MODAL = (By.CSS_SELECTOR, "[data-testid='mode-modal']")
MODE_CARD_MANUAL = (By.CSS_SELECTOR, "[data-testid='mode-card-manual']")
MANUAL_EDITOR = (By.CSS_SELECTOR, "[data-testid='manual-editor']")
EDITOR_BREADCRUMB = (By.CSS_SELECTOR, "[data-testid='manual-editor'] [data-testid='editor-breadcrumb']")

EXPECTED_DOKLAD_BREADCRUMB = "Доклад · Ручной режим"


class ManualEditorStatements(BaseFrontendStatements):
    def open_manual_editor_for_doklad(self, driver: WebDriver, app_url: str) -> None:
        self.navigate_to_doklad_type_modal(driver, app_url)
        self._wait_for_visible(driver, MODE_CARD_MANUAL).click()

    def assert_mode_modal_is_closed(self, driver: WebDriver) -> None:
        WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(
            ec.invisibility_of_element_located(MODE_MODAL)
        )

    def assert_manual_editor_is_open_for_doklad(self, driver: WebDriver) -> None:
        self._wait_for_visible(driver, MANUAL_EDITOR)

        breadcrumb = self._wait_for_visible(driver, EDITOR_BREADCRUMB)
        actual_breadcrumb = breadcrumb.text.strip()
        assert actual_breadcrumb == EXPECTED_DOKLAD_BREADCRUMB, (
            f"expected editor breadcrumb '{EXPECTED_DOKLAD_BREADCRUMB}', got '{actual_breadcrumb}'"
        )
