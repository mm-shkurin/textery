import uuid
from typing import ClassVar

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver

from statements.frontend.base_frontend_statements import BaseFrontendStatements

EMAIL_INPUT = (By.CSS_SELECTOR, "[data-testid='register-email-input']")
PASSWORD_INPUT = (By.CSS_SELECTOR, "[data-testid='register-password-input']")
CONFIRM_PASSWORD_INPUT = (By.CSS_SELECTOR, "[data-testid='register-confirm-password-input']")
SUBMIT_BUTTON = (By.CSS_SELECTOR, "[data-testid='register-submit-button']")
LOADING_INDICATOR = (By.CSS_SELECTOR, "[data-testid='register-loading-indicator']")
PASSWORD_ERROR = (By.CSS_SELECTOR, "[data-testid='register-password-error']")
EMAIL_ERROR = (By.CSS_SELECTOR, "[data-testid='register-email-error']")
CONFIRM_ERROR = (By.CSS_SELECTOR, "[data-testid='register-confirm-error']")
LOGIN_LINK = (By.CSS_SELECTOR, "[data-testid='register-login-link']")
REGISTER_REQUEST_PATH = "/api/v1/auth/register"


class RegisterPageStatements(BaseFrontendStatements):
    # Values are authoritative from the mockup HTML
    # (ProductSpecification/stories/07-authorization/mockups/desktop/01-register.html),
    # which the frontend implementation must match exactly.
    EXPECTED_EMAIL_PLACEHOLDER: ClassVar[str] = "email@example.ru"
    EXPECTED_PASSWORD_PLACEHOLDER: ClassVar[str] = "Минимум 8 символов"
    EXPECTED_CONFIRM_PASSWORD_PLACEHOLDER: ClassVar[str] = "Повторите пароль"
    EXPECTED_SUBMIT_BUTTON_TEXT: ClassVar[str] = "Зарегистрироваться"
    # Satisfies the password policy (see utils/passwordPolicy.ts) so the client-side
    # guard never masks the server's duplicate-email response.
    REGISTERED_ACCOUNT_PASSWORD: ClassVar[str] = "Str0ng!Pass"
    # Unlike the constants above, this one is NOT mockup-owned: it is the backend's
    # own 409 EMAIL_ALREADY_REGISTERED message, which RegisterForm.tsx renders
    # verbatim (`applyRegisterError` returns `apiError.message` untranslated). The
    # scenario's point is that the *server's* error reaches the email field, so this
    # must stay the server's exact text — asserting a client-owned string would pass
    # even if the response never arrived. If the backend rewords the message, this
    # test is *supposed* to fail: that is the coupling working, not a brittle test.
    EXPECTED_DUPLICATE_EMAIL_MESSAGE: ClassVar[str] = "An account with this email address already exists."

    def navigate_to_register_page(self, driver: WebDriver, app_url: str) -> None:
        driver.get(f"{app_url}/register")

    def assert_url_is_register_page(self, driver: WebDriver, app_url: str) -> None:
        self._assert_url_path(driver, app_url, "/register")

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

    def assert_loading_indicator_is_visible(self, driver: WebDriver) -> None:
        self._assert_visible(driver, LOADING_INDICATOR, "loading indicator")

    def fill_password_field(self, driver: WebDriver, password: str) -> None:
        self._wait_for_visible(driver, PASSWORD_INPUT).send_keys(password)

    def blur_password_field(self, driver: WebDriver) -> None:
        self._wait_for_visible(driver, PASSWORD_INPUT).send_keys(Keys.TAB)

    def assert_password_policy_error_is_visible(self, driver: WebDriver, expected_text: str) -> None:
        self._assert_hint_error_visible(driver, PASSWORD_ERROR, expected_text, "password policy error")

    def fill_confirm_password_field(self, driver: WebDriver, confirm: str) -> None:
        self._wait_for_visible(driver, CONFIRM_PASSWORD_INPUT).send_keys(confirm)

    def blur_confirm_password_field(self, driver: WebDriver) -> None:
        self._wait_for_visible(driver, CONFIRM_PASSWORD_INPUT).send_keys(Keys.TAB)

    def assert_confirm_mismatch_error_is_visible(self, driver: WebDriver, expected_text: str) -> None:
        self._assert_hint_error_visible(driver, CONFIRM_ERROR, expected_text, "confirm mismatch error")

    def given_an_account_already_registered(self, driver: WebDriver, app_url: str) -> str:
        """Registers a brand-new account through the UI and returns its email.

        The email is freshly generated per run, so this scenario owns the row it
        later collides with. The alternative — hardcoding a known-duplicate like
        `newuser@example.ru` — would couple this test to a row another test
        happened to create, in a shared DB with no cleanup fixture: it would pass
        or fail depending on run order and on whether that other test ran at all.

        Landing on /verify is the proof the first registration really succeeded,
        so a later duplicate error can only come from the server rejecting the
        second attempt.
        """
        email = f"duplicate-{uuid.uuid4().hex}@example.ru"
        self.navigate_to_register_page(driver, app_url)
        self.submit_registration_with_email(driver, email)
        self._assert_url_path(driver, app_url, "/verify")
        return email

    def submit_registration_with_email(self, driver: WebDriver, email: str) -> None:
        self.fill_registration_form(
            driver, email, self.REGISTERED_ACCOUNT_PASSWORD, self.REGISTERED_ACCOUNT_PASSWORD
        )
        self.click_submit_button(driver)

    def assert_duplicate_email_error_is_visible(self, driver: WebDriver) -> None:
        """Asserts the server's duplicate-email error is displayed *near the email
        field* — the scenario's Then clause. Both halves are load-bearing: the text
        check proves the server's message arrived, the container check proves it
        landed against the email field rather than somewhere else on the page.
        """
        self._assert_hint_error_visible(
            driver, EMAIL_ERROR, self.EXPECTED_DUPLICATE_EMAIL_MESSAGE, "duplicate email error"
        )
        self._assert_error_shares_field_container_with_input(
            driver, EMAIL_ERROR, EMAIL_INPUT, "duplicate email error"
        )

    def click_login_link(self, driver: WebDriver) -> None:
        self._wait_for_visible(driver, LOGIN_LINK).click()

    def assert_no_duplicate_registration_request(self, driver: WebDriver) -> None:
        request_count = self._count_requests_to(driver, REGISTER_REQUEST_PATH)
        assert request_count == 1, (
            f"expected exactly 1 request to {REGISTER_REQUEST_PATH} "
            f"(no duplicate submission), got {request_count}"
        )
