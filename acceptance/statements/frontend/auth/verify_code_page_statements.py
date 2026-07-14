from typing import ClassVar

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from statements.frontend.base_frontend_statements import BaseFrontendStatements

CODE_INPUT_COUNT = 6
RESEND_BUTTON = (By.CSS_SELECTOR, "[data-testid='verify-resend-button']")
RESEND_COUNTDOWN = (By.CSS_SELECTOR, "[data-testid='verify-resend-countdown']")


def _code_input_locator(index: int) -> tuple[str, str]:
    return (By.CSS_SELECTOR, f"[data-testid='verify-code-input-{index}']")


class VerifyCodePageStatements(BaseFrontendStatements):
    # Values are authoritative from the mockup HTML
    # (ProductSpecification/stories/07-authorization/mockups/desktop/02-verify-code.html)
    # and the 60s resend cooldown in 07_Authorization_Notes.md, which the frontend
    # implementation must match exactly.
    EXPECTED_RESEND_LINK_TEXT: ClassVar[str] = "Письмо не пришло? Отправить код повторно"
    EXPECTED_CODE_INPUT_TYPE: ClassVar[str] = "text"
    EXPECTED_CODE_INPUT_INPUTMODE: ClassVar[str] = "numeric"
    # Initial countdown on page load equals the full 60s resend cooldown, mm:ss format.
    EXPECTED_INITIAL_COUNTDOWN_TEXT: ClassVar[str] = "01:00"

    def navigate_to_verify_code_page(self, driver: WebDriver, app_url: str) -> None:
        driver.get(f"{app_url}/verify")

    def assert_six_code_inputs_are_visible(self, driver: WebDriver) -> None:
        for index in range(CODE_INPUT_COUNT):
            element = self._wait_for_visible(driver, _code_input_locator(index))
            assert element.is_displayed(), f"expected code input {index} to be visible"
            assert element.get_attribute("maxlength") == "1", (
                f"expected code input {index} maxlength '1', got "
                f"'{element.get_attribute('maxlength')}'"
            )
            assert element.get_attribute("type") == self.EXPECTED_CODE_INPUT_TYPE, (
                f"expected code input {index} type '{self.EXPECTED_CODE_INPUT_TYPE}', got "
                f"'{element.get_attribute('type')}'"
            )
            assert element.get_attribute("inputmode") == self.EXPECTED_CODE_INPUT_INPUTMODE, (
                f"expected code input {index} inputmode '{self.EXPECTED_CODE_INPUT_INPUTMODE}', "
                f"got '{element.get_attribute('inputmode')}'"
            )

    def type_digit_into_code_input(self, driver: WebDriver, index: int, digit: str) -> None:
        element = self._wait_for_visible(driver, _code_input_locator(index))
        element.send_keys(digit)

    def assert_focus_is_on_code_input(self, driver: WebDriver, index: int) -> None:
        active_element = driver.switch_to.active_element
        expected_element = driver.find_element(*_code_input_locator(index))
        assert active_element == expected_element, (
            f"expected focus on code input {index}, but a different element is focused"
        )

    def assert_code_input_has_value(self, driver: WebDriver, index: int, value: str) -> None:
        element = driver.find_element(*_code_input_locator(index))
        actual = element.get_attribute("value")
        assert actual == value, (
            f"expected code input {index} value '{value}', got '{actual}'"
        )

    def assert_resend_action_with_countdown_is_visible(self, driver: WebDriver) -> None:
        link = self._wait_for_visible(driver, RESEND_BUTTON)
        assert link.is_displayed(), "expected resend action to be visible"
        assert link.text.strip() == self.EXPECTED_RESEND_LINK_TEXT, (
            f"expected resend action text '{self.EXPECTED_RESEND_LINK_TEXT}', got '{link.text}'"
        )

        countdown = self._wait_for_visible(driver, RESEND_COUNTDOWN)
        assert countdown.is_displayed(), "expected resend countdown to be visible"
        assert countdown.text.strip() == self.EXPECTED_INITIAL_COUNTDOWN_TEXT, (
            f"expected resend countdown '{self.EXPECTED_INITIAL_COUNTDOWN_TEXT}', "
            f"got '{countdown.text}'"
        )
