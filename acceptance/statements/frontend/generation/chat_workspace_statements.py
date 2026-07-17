from typing import ClassVar

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from statements.frontend.base_frontend_statements import BaseFrontendStatements

PRIMARY_CTA_BUTTON = (By.CSS_SELECTOR, "[data-testid='header-primary-cta-button']")
TYPE_CARD_DOKLAD = (By.CSS_SELECTOR, "[data-testid='type-card-doklad']")
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
        driver.get(app_url)
        self._given_signed_in(driver)
        self._wait_for_visible(driver, PRIMARY_CTA_BUTTON).click()
        self._wait_for_visible(driver, TYPE_CARD_DOKLAD).click()
        self._wait_for_visible(driver, MODE_CARD_AUTO).click()

    @staticmethod
    def _given_signed_in(driver: WebDriver) -> None:
        """Put a session in place so the landing CTA opens the flow instead of bouncing to /login.

        Story 7 put generation behind a session (landing stays public, everything behind it does
        not), so this is now a precondition of scenario 4.1 rather than part of its subject.

        Seeds the session directly instead of driving register -> verify -> login through the UI:
        this scenario is about the chat panel, and routing it through three auth screens would
        make every generation test fail whenever auth breaks, hiding which layer is at fault.
        The gate only checks for a token's PRESENCE, so a placeholder satisfies it honestly.

        The day the backend starts requiring `Authorization`, this stops being enough — a fake
        token will pass the client gate and the real API will refuse. At that point this must
        become a real sign-in. Verified 2026-07-16: `POST /api/v1/generations` still serves
        anonymous callers, so today the seeded token is not hiding anything.
        """
        driver.execute_script(
            "window.sessionStorage.setItem('textery.auth.accessToken', arguments[0]);"
            "window.sessionStorage.setItem('textery.auth.refreshToken', arguments[0]);",
            "acceptance-test-token",
        )
        driver.refresh()

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
        self._assert_submit_button_visible(
            driver, TOPIC_SEND_BUTTON, self.EXPECTED_SEND_BUTTON_TEXT, expected_type=None
        )
        self._assert_disabled(driver, TOPIC_SEND_BUTTON, "send button")
