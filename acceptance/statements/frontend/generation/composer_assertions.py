"""Shared assertions for the topic composer (`frontend/src/features/generation/components/Composer.tsx`).

Both the chat-workspace suite (scenario 4.1) and the unified create flow (story 18,
scenario 1.1) assert the same composer is ready for a topic: the input prompts with the
expected placeholder and starts empty, and the send button carries the expected label but
refuses to fire until there is a topic. Those checks lived in duplicate — line for line,
failure messages included — so a copy change in the component had two call sites to find.

The locators and expected copy stay in `composer_locators.py`; this module holds only the
assertions over them. Mixed into a `BaseFrontendStatements` subclass, which supplies
`_wait_for_visible`, `_assert_element_text_equals`, and `_assert_disabled`.
"""

from selenium.webdriver.remote.webdriver import WebDriver

from statements.frontend.generation.composer_locators import (
    EXPECTED_SEND_BUTTON_TEXT,
    EXPECTED_TOPIC_INPUT_PLACEHOLDER,
    TOPIC_INPUT,
    TOPIC_SEND_BUTTON,
)


class ComposerAssertionsMixin:
    """Assertions that the topic composer is present and ready to accept a topic."""

    def _assert_topic_input_empty_and_prompting(self, driver: WebDriver) -> None:
        """The composer is visible, prompts for a topic, and carries no stale text.

        Presence alone would pass on a composer pre-filled with a previous run's topic,
        so both the placeholder copy and the empty value are pinned to exact values.
        """
        element = self._wait_for_visible(driver, TOPIC_INPUT)
        placeholder = element.get_attribute("placeholder")
        assert placeholder == EXPECTED_TOPIC_INPUT_PLACEHOLDER, (
            f"expected topic input placeholder '{EXPECTED_TOPIC_INPUT_PLACEHOLDER}', got '{placeholder}'"
        )
        value = element.get_attribute("value")
        assert value == "", f"expected topic input to start empty, got '{value}'"

    def _assert_send_button_idle(self, driver: WebDriver) -> None:
        """The send button is present with the expected label and refuses to fire while empty."""
        self._assert_element_text_equals(
            driver, TOPIC_SEND_BUTTON, EXPECTED_SEND_BUTTON_TEXT, "send button text"
        )
        self._assert_disabled(driver, TOPIC_SEND_BUTTON, "send button")
