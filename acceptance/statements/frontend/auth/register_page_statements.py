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
        self._assert_field_visible(
            driver, EMAIL_INPUT, "email", self.EXPECTED_EMAIL_PLACEHOLDER, "email field"
        )

    def assert_password_field_is_visible(self, driver: WebDriver) -> None:
        self._assert_field_visible(
            driver, PASSWORD_INPUT, "password", self.EXPECTED_PASSWORD_PLACEHOLDER, "password field"
        )

    def assert_confirm_password_field_is_visible(self, driver: WebDriver) -> None:
        self._assert_field_visible(
            driver,
            CONFIRM_PASSWORD_INPUT,
            "password",
            self.EXPECTED_CONFIRM_PASSWORD_PLACEHOLDER,
            "confirm password field",
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

    def _assert_field_visible(
        self,
        driver: WebDriver,
        locator: tuple[str, str],
        expected_type: str,
        expected_placeholder: str,
        label: str,
    ) -> None:
        element = self._wait_for_visible(driver, locator)
        assert element.is_displayed(), f"expected {label} to be visible"
        assert element.get_attribute("type") == expected_type, (
            f"expected {label} type '{expected_type}', got '{element.get_attribute('type')}'"
        )
        assert element.get_attribute("placeholder") == expected_placeholder, (
            f"expected {label} placeholder '{expected_placeholder}', "
            f"got '{element.get_attribute('placeholder')}'"
        )
