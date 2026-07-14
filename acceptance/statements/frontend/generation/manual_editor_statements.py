from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from statements.frontend.base_frontend_statements import BaseFrontendStatements, WAIT_TIMEOUT_SECONDS
from statements.frontend.generation.mode_modal_statements import MODE_CARD_MANUAL, MODE_MODAL

MANUAL_EDITOR_SELECTOR = "[data-testid='manual-editor']"
MANUAL_EDITOR = (By.CSS_SELECTOR, MANUAL_EDITOR_SELECTOR)
EDITOR_BREADCRUMB = (By.CSS_SELECTOR, f"{MANUAL_EDITOR_SELECTOR} [data-testid='editor-breadcrumb']")
LOADING_SKELETON = (By.CSS_SELECTOR, f"{MANUAL_EDITOR_SELECTOR} .me-loading-skeleton")
CONTENT_PLACEHOLDER = (By.CSS_SELECTOR, f"{MANUAL_EDITOR_SELECTOR} .me-placeholder")
TOOLBAR_BUTTON = (By.CSS_SELECTOR, f"{MANUAL_EDITOR_SELECTOR} .me-toolbar-btn")
CONTENT_AREA = (By.CSS_SELECTOR, f"{MANUAL_EDITOR_SELECTOR} .me-content-area")
BOLD_TEXT = (By.CSS_SELECTOR, f"{MANUAL_EDITOR_SELECTOR} .me-content-area strong")

EXPECTED_DOKLAD_BREADCRUMB = "Доклад · Ручной режим"
EXPECTED_PLACEHOLDER_TEXT = "Начните печатать…"

TOOLBAR_BUTTON_ARIA_LABELS = {
    "heading": ["Заголовок 1", "Заголовок 2"],
    "paragraph": ["Абзац"],
    "list": ["Маркированный список", "Нумерованный список"],
    "bold": ["Жирный"],
    "italic": ["Курсив"],
}
EXPECTED_TOOLBAR_BUTTON_COUNT = 7
BOLD_BUTTON = (
    By.CSS_SELECTOR,
    f"{MANUAL_EDITOR_SELECTOR} .me-toolbar-btn[aria-label='{TOOLBAR_BUTTON_ARIA_LABELS['bold'][0]}']",
)


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
        self._assert_element_text_equals(
            driver, EDITOR_BREADCRUMB, EXPECTED_DOKLAD_BREADCRUMB, "editor breadcrumb"
        )

    def assert_no_loading_skeleton_is_shown(self, driver: WebDriver) -> None:
        # Wait for the editor shell to mount before asserting absence, so the
        # check can't pass vacuously by running before a skeleton would appear.
        self._wait_for_visible(driver, MANUAL_EDITOR)
        skeleton_elements = driver.find_elements(*LOADING_SKELETON)
        assert not skeleton_elements, (
            f"expected no loading skeleton, found {len(skeleton_elements)} element(s)"
        )

    def assert_content_placeholder_is_visible(self, driver: WebDriver) -> None:
        self._assert_element_text_equals(
            driver, CONTENT_PLACEHOLDER, EXPECTED_PLACEHOLDER_TEXT, "content placeholder text"
        )

    def assert_toolbar_controls_are_visible(self, driver: WebDriver) -> None:
        self._assert_each_toolbar_button_is_enabled(driver)
        self._assert_toolbar_button_count(driver)

    def _assert_each_toolbar_button_is_enabled(self, driver: WebDriver) -> None:
        for control_name, aria_labels in TOOLBAR_BUTTON_ARIA_LABELS.items():
            for aria_label in aria_labels:
                locator = (By.CSS_SELECTOR, f"{MANUAL_EDITOR_SELECTOR} .me-toolbar-btn[aria-label='{aria_label}']")
                button = self._wait_for_visible(driver, locator)
                assert button.is_enabled(), (
                    f"expected {control_name} toolbar control '{aria_label}' to be enabled"
                )

    def _assert_toolbar_button_count(self, driver: WebDriver) -> None:
        toolbar_buttons = driver.find_elements(*TOOLBAR_BUTTON)
        assert len(toolbar_buttons) == EXPECTED_TOOLBAR_BUTTON_COUNT, (
            f"expected exactly {EXPECTED_TOOLBAR_BUTTON_COUNT} toolbar controls, "
            f"found {len(toolbar_buttons)}"
        )

    def type_text_in_editor(self, driver: WebDriver, text: str) -> None:
        content_area = self._wait_for_visible(driver, CONTENT_AREA)
        content_area.click()
        content_area.send_keys(text)

    def select_all_text_in_editor(self, driver: WebDriver) -> None:
        content_area = self._wait_for_visible(driver, CONTENT_AREA)
        content_area.click()
        ActionChains(driver).key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).perform()

    def apply_bold_formatting(self, driver: WebDriver) -> None:
        self._wait_for_visible(driver, BOLD_BUTTON).click()

    def assert_selected_text_is_bold(self, driver: WebDriver, expected_text: str) -> None:
        self._assert_element_text_equals(driver, BOLD_TEXT, expected_text, "bold text")

    def assert_bold_button_is_active(self, driver: WebDriver) -> None:
        button = self._wait_for_visible(driver, BOLD_BUTTON)
        pressed = button.get_attribute("aria-pressed")
        assert pressed == "true", f"expected bold toolbar button to be aria-pressed='true', got '{pressed}'"
