from typing import ClassVar
from urllib.parse import urlparse

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.wait import WebDriverWait

from statements.frontend.base_frontend_statements import WAIT_TIMEOUT_SECONDS, BaseFrontendStatements

EMAIL_INPUT = (By.CSS_SELECTOR, "[data-testid='login-email-input']")
PASSWORD_INPUT = (By.CSS_SELECTOR, "[data-testid='login-password-input']")
SUBMIT_BUTTON = (By.CSS_SELECTOR, "[data-testid='login-submit-button']")
PASSWORD_TOGGLE = (By.CSS_SELECTOR, "[data-testid='login-password-toggle']")
LOADING_INDICATOR = (By.CSS_SELECTOR, "[data-testid='login-loading-indicator']")


class LoginPageStatements(BaseFrontendStatements):
    # Values are authoritative from the mockup HTML
    # (ProductSpecification/stories/07-authorization/mockups/desktop/03-login.html),
    # which the frontend implementation must match exactly.
    EXPECTED_EMAIL_PLACEHOLDER: ClassVar[str] = "email@example.ru"
    EXPECTED_PASSWORD_PLACEHOLDER: ClassVar[str] = "Пароль"
    EXPECTED_SUBMIT_BUTTON_TEXT: ClassVar[str] = "Войти"

    def navigate_to_login_page(self, driver: WebDriver, app_url: str) -> None:
        driver.get(f"{app_url}/login")

    _DEFAULT_PORTS: ClassVar[dict[str, str]] = {"http": "80", "https": "443"}

    @classmethod
    def _normalized_origin(cls, url: str) -> tuple[str, str]:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        port = str(parsed.port) if parsed.port else cls._DEFAULT_PORTS.get(parsed.scheme, "")
        return parsed.scheme, f"{host}:{port}" if port else host

    def assert_url_is_login_page(self, driver: WebDriver, app_url: str) -> None:
        expected_origin = self._normalized_origin(app_url)

        def is_login_page(d: WebDriver) -> bool:
            actual = urlparse(d.current_url)
            return (
                self._normalized_origin(d.current_url) == expected_origin
                and actual.path.rstrip("/") == "/login"
            )

        WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(
            is_login_page, f"expected URL '{app_url}/login', got '{driver.current_url}'"
        )

    def assert_email_field_is_visible(self, driver: WebDriver) -> None:
        self._assert_field_visible(
            driver, EMAIL_INPUT, "email", self.EXPECTED_EMAIL_PLACEHOLDER, "email field"
        )

    def assert_password_field_is_visible(self, driver: WebDriver) -> None:
        self._assert_field_visible(
            driver, PASSWORD_INPUT, "password", self.EXPECTED_PASSWORD_PLACEHOLDER, "password field"
        )

    def assert_submit_button_is_visible(self, driver: WebDriver) -> None:
        self._assert_submit_button_visible(driver, SUBMIT_BUTTON, self.EXPECTED_SUBMIT_BUTTON_TEXT)

    def assert_password_field_is_masked(self, driver: WebDriver) -> None:
        element = self._wait_for_visible(driver, PASSWORD_INPUT)
        assert element.get_attribute("type") == "password", (
            f"expected password field type 'password', got '{element.get_attribute('type')}'"
        )

    def click_show_password_toggle(self, driver: WebDriver) -> None:
        toggle = self._wait_for_visible(driver, PASSWORD_TOGGLE)
        toggle.click()

    def assert_password_field_is_plain_text(self, driver: WebDriver) -> None:
        element = self._wait_for_visible(driver, PASSWORD_INPUT)
        assert element.get_attribute("type") == "text", (
            f"expected password field type 'text', got '{element.get_attribute('type')}'"
        )

    def fill_login_form(self, driver: WebDriver, email: str, password: str) -> None:
        self._wait_for_visible(driver, EMAIL_INPUT).send_keys(email)
        self._wait_for_visible(driver, PASSWORD_INPUT).send_keys(password)

    def click_submit_button(self, driver: WebDriver) -> None:
        self._wait_for_visible(driver, SUBMIT_BUTTON).click()

    def assert_submit_button_is_disabled(self, driver: WebDriver) -> None:
        self._assert_disabled(driver, SUBMIT_BUTTON, "submit button")

    def assert_loading_indicator_is_visible(self, driver: WebDriver) -> None:
        self._assert_visible(driver, LOADING_INDICATOR, "loading indicator")
