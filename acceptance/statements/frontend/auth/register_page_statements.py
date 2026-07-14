from typing import ClassVar

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from statements.frontend.base_frontend_statements import BaseFrontendStatements

EMAIL_INPUT = (By.CSS_SELECTOR, "[data-testid='register-email-input']")
PASSWORD_INPUT = (By.CSS_SELECTOR, "[data-testid='register-password-input']")
CONFIRM_PASSWORD_INPUT = (By.CSS_SELECTOR, "[data-testid='register-confirm-password-input']")
SUBMIT_BUTTON = (By.CSS_SELECTOR, "[data-testid='register-submit-button']")
REGISTER_REQUEST_PATH = "/api/v1/auth/register"


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
        self._assert_submit_button_visible(driver, SUBMIT_BUTTON, self.EXPECTED_SUBMIT_BUTTON_TEXT)

    def fill_registration_form(self, driver: WebDriver, email: str, password: str, confirm: str) -> None:
        self._wait_for_visible(driver, EMAIL_INPUT).send_keys(email)
        self._wait_for_visible(driver, PASSWORD_INPUT).send_keys(password)
        self._wait_for_visible(driver, CONFIRM_PASSWORD_INPUT).send_keys(confirm)

    def click_submit_button(self, driver: WebDriver) -> None:
        self._wait_for_visible(driver, SUBMIT_BUTTON).click()

    def assert_submit_button_is_disabled(self, driver: WebDriver) -> None:
        self._assert_disabled(driver, SUBMIT_BUTTON, "submit button")

    def click_submit_button_ignoring_disabled_state(self, driver: WebDriver) -> None:
        """Dispatches a raw click at the submit button even while it is
        disabled. A native Selenium `.click()` on a `disabled` element is a
        no-op (or raises), which is exactly what we need to distinguish from
        an app bug: this method proves a second user click cannot reach the
        submit handler, so it must bypass Selenium's own disabled-guard via
        JS and let the browser's native disabled-button semantics decide.
        """
        element = self._wait_for_visible(driver, SUBMIT_BUTTON)
        driver.execute_script("arguments[0].click();", element)

    def assert_no_duplicate_registration_request(self, driver: WebDriver) -> None:
        request_count = self._count_requests_to(driver, REGISTER_REQUEST_PATH)
        assert request_count == 1, (
            f"expected exactly 1 request to {REGISTER_REQUEST_PATH} "
            f"(no duplicate submission), got {request_count}"
        )
