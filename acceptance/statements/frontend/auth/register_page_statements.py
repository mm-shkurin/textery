from typing import ClassVar

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from statements.frontend.base_frontend_statements import BaseFrontendStatements

EMAIL_INPUT = (By.CSS_SELECTOR, "[data-testid='register-email-input']")
PASSWORD_INPUT = (By.CSS_SELECTOR, "[data-testid='register-password-input']")
CONFIRM_PASSWORD_INPUT = (By.CSS_SELECTOR, "[data-testid='register-confirm-password-input']")
SUBMIT_BUTTON = (By.CSS_SELECTOR, "[data-testid='register-submit-button']")


class RegisterPageStatements(BaseFrontendStatements):
    # Values are authoritative from the mockup HTML
    # (ProductSpecification/stories/07-authorization/mockups/desktop/01-register.html),
    # which the frontend implementation must match exactly.
    EXPECTED_EMAIL_PLACEHOLDER: ClassVar[str] = "email@example.ru"
    EXPECTED_PASSWORD_PLACEHOLDER: ClassVar[str] = "Минимум 8 символов"
    EXPECTED_CONFIRM_PASSWORD_PLACEHOLDER: ClassVar[str] = "Повторите пароль"
    EXPECTED_SUBMIT_BUTTON_TEXT: ClassVar[str] = "Зарегистрироваться"

    def navigate_to_register_page(self, driver: WebDriver, app_url: str) -> None:
        driver.get(f"{app_url}/register")

    def assert_email_field_is_visible(self, driver: WebDriver) -> None:
        element = self._wait_for_visible(driver, EMAIL_INPUT)
        assert element.is_displayed(), "expected email field to be visible"
        assert element.get_attribute("type") == "email", (
            f"expected email field type 'email', got '{element.get_attribute('type')}'"
        )
        assert element.get_attribute("placeholder") == self.EXPECTED_EMAIL_PLACEHOLDER, (
            f"expected email field placeholder '{self.EXPECTED_EMAIL_PLACEHOLDER}', "
            f"got '{element.get_attribute('placeholder')}'"
        )

    def assert_password_field_is_visible(self, driver: WebDriver) -> None:
        element = self._wait_for_visible(driver, PASSWORD_INPUT)
        assert element.is_displayed(), "expected password field to be visible"
        assert element.get_attribute("type") == "password", (
            f"expected password field type 'password', got '{element.get_attribute('type')}'"
        )
        assert element.get_attribute("placeholder") == self.EXPECTED_PASSWORD_PLACEHOLDER, (
            f"expected password field placeholder '{self.EXPECTED_PASSWORD_PLACEHOLDER}', "
            f"got '{element.get_attribute('placeholder')}'"
        )

    def assert_confirm_password_field_is_visible(self, driver: WebDriver) -> None:
        element = self._wait_for_visible(driver, CONFIRM_PASSWORD_INPUT)
        assert element.is_displayed(), "expected confirm password field to be visible"
        assert element.get_attribute("type") == "password", (
            f"expected confirm password field type 'password', got '{element.get_attribute('type')}'"
        )
        assert element.get_attribute("placeholder") == self.EXPECTED_CONFIRM_PASSWORD_PLACEHOLDER, (
            f"expected confirm password field placeholder "
            f"'{self.EXPECTED_CONFIRM_PASSWORD_PLACEHOLDER}', got "
            f"'{element.get_attribute('placeholder')}'"
        )

    def assert_submit_button_is_visible(self, driver: WebDriver) -> None:
        element = self._wait_for_visible(driver, SUBMIT_BUTTON)
        assert element.is_displayed(), "expected submit button to be visible"
        assert element.get_attribute("type") == "submit", (
            f"expected submit button type 'submit', got '{element.get_attribute('type')}'"
        )
        assert element.text.strip() == self.EXPECTED_SUBMIT_BUTTON_TEXT, (
            f"expected submit button text '{self.EXPECTED_SUBMIT_BUTTON_TEXT}', got '{element.text}'"
        )
