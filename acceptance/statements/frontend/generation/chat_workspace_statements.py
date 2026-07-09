from typing import ClassVar

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

PRIMARY_CTA_BUTTON = (By.CSS_SELECTOR, "[data-testid='hero-primary-cta-button']")
TYPE_CARD_DOKLAD = (By.CSS_SELECTOR, "[data-testid='type-card-doklad']")
MODE_CARD_AUTO = (By.CSS_SELECTOR, "[data-testid='mode-card-auto']")

BREADCRUMB_CHIP = (By.CSS_SELECTOR, "[data-testid='chat-breadcrumb-chip']")
CHAT_INPUT = (By.CSS_SELECTOR, "[data-testid='chat-input']")
CHAT_SEND_BUTTON = (By.CSS_SELECTOR, "[data-testid='chat-send-button']")

WAIT_TIMEOUT_SECONDS = 5


class ChatWorkspaceStatements:
    # "Доклад" is the only document type currently selectable (type modal, scenario
    # 2.1) -- the breadcrumb chip must echo that choice, not a hardcoded label.
    EXPECTED_BREADCRUMB_TEXT: ClassVar[str] = "Доклад"

    # No mockup covers this doc-left/chat-right screen (known-debt #8 replaced the
    # standalone generation-form mockup -- ProductSpecification/stories/01-auto-generate-doklad/
    # mockups/desktop/04-generation-form.html -- with this chat panel, and that mockup's
    # chat screens (05-07) start after the first message, not at this initial empty
    # state). The test is the spec for this copy, decided now rather than deferred:
    # the input placeholder follows the example-driven convention already used by that
    # mockup's fields (e.g. "Например: ..."), and the send button reuses the
    # visible-text button convention used throughout every mockup (btn-primary always
    # carries visible text, e.g. "Сгенерировать", "Попробовать бесплатно") rather than
    # an icon-only control.
    EXPECTED_CHAT_INPUT_PLACEHOLDER: ClassVar[str] = "Например: расскажи, что нужно доработать"
    EXPECTED_SEND_BUTTON_TEXT: ClassVar[str] = "Отправить"

    def navigate_to_chat_workspace_for_doklad(self, driver: WebDriver, app_url: str) -> None:
        driver.get(app_url)
        self._wait_for_visible(driver, PRIMARY_CTA_BUTTON).click()
        self._wait_for_visible(driver, TYPE_CARD_DOKLAD).click()
        self._wait_for_visible(driver, MODE_CARD_AUTO).click()

    def assert_breadcrumb_chip_shows_document_type(self, driver: WebDriver) -> None:
        self._assert_element_visible_with_text(
            driver, BREADCRUMB_CHIP, self.EXPECTED_BREADCRUMB_TEXT, "breadcrumb chip"
        )

    def assert_chat_input_is_visible(self, driver: WebDriver) -> None:
        element = self._wait_for_visible(driver, CHAT_INPUT)
        assert element.is_displayed(), "expected chat input to be visible"
        placeholder = element.get_attribute("placeholder")
        assert placeholder == self.EXPECTED_CHAT_INPUT_PLACEHOLDER, (
            f"expected chat input placeholder '{self.EXPECTED_CHAT_INPUT_PLACEHOLDER}', got '{placeholder}'"
        )

    def assert_send_button_is_visible(self, driver: WebDriver) -> None:
        self._assert_element_visible_with_text(
            driver, CHAT_SEND_BUTTON, self.EXPECTED_SEND_BUTTON_TEXT, "send button"
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
