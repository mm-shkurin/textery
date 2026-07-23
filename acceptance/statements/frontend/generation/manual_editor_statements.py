from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from statements.frontend.base_frontend_statements import BaseFrontendStatements, WAIT_TIMEOUT_SECONDS
from statements.frontend.generation.mode_modal_statements import MODE_CARD_MANUAL, MODE_MODAL

MANUAL_EDITOR_SELECTOR = "[data-testid='manual-editor']"
MANUAL_EDITOR = (By.CSS_SELECTOR, MANUAL_EDITOR_SELECTOR)
EDITOR_BREADCRUMB = (By.CSS_SELECTOR, f"{MANUAL_EDITOR_SELECTOR} [data-testid='editor-breadcrumb']")
LOADING_SKELETON = (By.CSS_SELECTOR, f"{MANUAL_EDITOR_SELECTOR} .me-loading-skeleton")
TOOLBAR_BUTTON = (By.CSS_SELECTOR, f"{MANUAL_EDITOR_SELECTOR} .me-toolbar-btn")
# The typeable target is the ProseMirror contenteditable div rendered by <EditorContent>,
# not the .me-content-area wrapper. It carries data-testid="editor-content-area" (set via
# useEditor editorProps.attributes) and is the element send_keys/click must reach.
EDITABLE_CONTENT = (
    By.CSS_SELECTOR, f"{MANUAL_EDITOR_SELECTOR} [data-testid='editor-content-area']"
)
BOLD_TEXT = (By.CSS_SELECTOR, f"{MANUAL_EDITOR_SELECTOR} .me-content-area strong")

EXPECTED_DOKLAD_BREADCRUMB = "Доклад · Ручной режим"
EXPECTED_PLACEHOLDER_TEXT = "Начните печатать…"

# The inline-only document schema has no block nodes, so H1/H2, paragraph, and the two list
# toggles were inert stubs and have been removed from the toolbar. The named controls scenario
# 2.1 asserts are the ones that actually work: the H3 heading (a mark, not a block node), bold,
# and italic.
TOOLBAR_BUTTON_ARIA_LABELS = {
    "heading": ["Заголовок 3"],
    "bold": ["Жирный"],
    "italic": ["Курсив"],
}
# Scenario 2.1 asserts the three working named controls above (H3, bold, italic) individually by
# aria-label. The toolbar carries 13 controls total (after the inert H1/H2/¶/list stubs were
# removed: H3, bold, italic, strike, underline, code, blockquote, hr, code-block, align-centre,
# link, undo, redo), so the count is a LOWER BOUND, not an exact match — pinning an exact total
# here would couple 2.1's test to the extended toolbar's size.
MINIMUM_TOOLBAR_BUTTON_COUNT = 3


def _toolbar_button_locator(aria_label: str) -> tuple[str, str]:
    return (By.CSS_SELECTOR, f"{MANUAL_EDITOR_SELECTOR} .me-toolbar-btn[aria-label='{aria_label}']")


BOLD_BUTTON = _toolbar_button_locator(TOOLBAR_BUTTON_ARIA_LABELS["bold"][0])


class ManualEditorStatements(BaseFrontendStatements):
    def open_manual_editor_for_doklad(self, driver: WebDriver, app_url: str) -> None:
        # A live session, not a seeded one: the editor calls createDocument on mount, and a
        # fake token 401s there — the app then clears the session and falls back to the landing.
        self.navigate_to_doklad_type_modal(driver, app_url, live_session=True)
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
        # The placeholder is not a DOM element. InlinePlaceholder decorates the empty
        # ProseMirror root with data-placeholder + is-editor-empty, and ManualEditor.css paints
        # the text via `.ProseMirror.is-editor-empty::before { content: attr(data-placeholder) }`.
        # jsdom cannot see the ::before paint, so this live computed-style check is exactly the
        # coverage the jsdom placeholder tests owe to selenium.
        content_area = self._wait_for_visible(driver, EDITABLE_CONTENT)
        actual_attr = content_area.get_attribute("data-placeholder")
        assert actual_attr == EXPECTED_PLACEHOLDER_TEXT, (
            f"expected data-placeholder='{EXPECTED_PLACEHOLDER_TEXT}', got '{actual_attr}'"
        )
        classes = (content_area.get_attribute("class") or "").split()
        assert "is-editor-empty" in classes, (
            f"expected the is-editor-empty class on the empty content area, got {classes}"
        )
        rendered = driver.execute_script(
            "return window.getComputedStyle(arguments[0], '::before').content", content_area
        )
        # getComputedStyle returns the painted string wrapped in quotes, e.g. '"Начните печатать…"'.
        assert rendered and EXPECTED_PLACEHOLDER_TEXT in rendered, (
            f"expected the ::before to paint '{EXPECTED_PLACEHOLDER_TEXT}', got {rendered!r}"
        )

    def assert_toolbar_controls_are_visible(self, driver: WebDriver) -> None:
        self._assert_each_toolbar_button_is_enabled(driver)
        self._assert_toolbar_button_count(driver)

    def _assert_each_toolbar_button_is_enabled(self, driver: WebDriver) -> None:
        for control_name, aria_labels in TOOLBAR_BUTTON_ARIA_LABELS.items():
            for aria_label in aria_labels:
                button = self._wait_for_visible(driver, _toolbar_button_locator(aria_label))
                assert button.is_enabled(), (
                    f"expected {control_name} toolbar control '{aria_label}' to be enabled"
                )

    def _assert_toolbar_button_count(self, driver: WebDriver) -> None:
        toolbar_buttons = driver.find_elements(*TOOLBAR_BUTTON)
        assert len(toolbar_buttons) >= MINIMUM_TOOLBAR_BUTTON_COUNT, (
            f"expected at least {MINIMUM_TOOLBAR_BUTTON_COUNT} toolbar controls, "
            f"found {len(toolbar_buttons)}"
        )

    def type_text_in_editor(self, driver: WebDriver, text: str) -> None:
        self._focus_content_area(driver).send_keys(text)

    def select_all_text_in_editor(self, driver: WebDriver) -> None:
        self._focus_content_area(driver)
        ActionChains(driver).key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).perform()

    def _focus_content_area(self, driver: WebDriver) -> WebElement:
        editable = self._wait_for_visible(driver, EDITABLE_CONTENT)
        editable.click()
        return editable

    def apply_bold_formatting(self, driver: WebDriver) -> None:
        self._wait_for_visible(driver, BOLD_BUTTON).click()

    def assert_selected_text_is_bold(self, driver: WebDriver, expected_text: str) -> None:
        self._assert_element_text_equals(driver, BOLD_TEXT, expected_text, "bold text")

    def assert_bold_button_is_active(self, driver: WebDriver) -> None:
        button = self._wait_for_visible(driver, BOLD_BUTTON)
        pressed = button.get_attribute("aria-pressed")
        assert pressed == "true", f"expected bold toolbar button to be aria-pressed='true', got '{pressed}'"
