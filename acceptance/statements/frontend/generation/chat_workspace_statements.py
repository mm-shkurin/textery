from typing import ClassVar

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from statements.frontend.base_frontend_statements import BaseFrontendStatements

MODE_CARD_AUTO = (By.CSS_SELECTOR, "[data-testid='mode-card-auto']")

CHAT_PANEL = (By.CSS_SELECTOR, "[data-testid='chat-panel']")
TOPIC_INPUT = (By.CSS_SELECTOR, "[data-testid='topic-input']")
TOPIC_SEND_BUTTON = (By.CSS_SELECTOR, "[data-testid='topic-send']")


class ChatWorkspaceStatements(BaseFrontendStatements):
    # Per known-debt #8, the standalone generation-form page (mockup 04) was replaced
    # by a single doc-left/chat-right screen; the "form fields" for scenario 4.1 are
    # now a single free-text composer in the chat panel, mapped to `topic` on submit.
    # Copy pulled from the actual built component
    # (frontend/src/features/generation/components/ChatWorkspace.tsx `Composer`),
    # not from the stale mockup 04 text.
    EXPECTED_TOPIC_INPUT_PLACEHOLDER: ClassVar[str] = (
        "Например: Влияние искусственного интеллекта на образование"
    )
    EXPECTED_SEND_BUTTON_TEXT: ClassVar[str] = "Сгенерировать"

    def navigate_to_chat_workspace_for_doklad(self, driver: WebDriver, app_url: str) -> None:
        self.navigate_to_doklad_type_modal(driver, app_url)
        self._wait_for_visible(driver, MODE_CARD_AUTO).click()

    def assert_chat_panel_is_visible(self, driver: WebDriver) -> None:
        element = self._wait_for_visible(driver, CHAT_PANEL)
        assert element.is_displayed(), "expected chat panel to be visible"

    def assert_topic_input_is_visible_and_empty(self, driver: WebDriver) -> None:
        element = self._wait_for_visible(driver, TOPIC_INPUT)
        assert element.is_displayed(), "expected topic input to be visible"
        placeholder = element.get_attribute("placeholder")
        assert placeholder == self.EXPECTED_TOPIC_INPUT_PLACEHOLDER, (
            f"expected topic input placeholder '{self.EXPECTED_TOPIC_INPUT_PLACEHOLDER}', got '{placeholder}'"
        )
        value = element.get_attribute("value")
        assert value == "", f"expected topic input to start empty, got '{value}'"

    def assert_send_button_is_visible_and_disabled(self, driver: WebDriver) -> None:
        element = self._assert_element_text_equals(
            driver, TOPIC_SEND_BUTTON, self.EXPECTED_SEND_BUTTON_TEXT, "send button text"
        )
        assert not element.is_enabled(), "expected send button to be disabled before any text is entered"
