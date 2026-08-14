from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from statements.frontend.base_frontend_statements import WAIT_TIMEOUT_SECONDS, BaseFrontendStatements

DELETE_BUTTON = (By.CSS_SELECTOR, "[data-testid='account-delete-button']")
CONFIRM_PANEL = (By.CSS_SELECTOR, "[data-testid='account-delete-confirm']")
PASSWORD_INPUT = (By.CSS_SELECTOR, "[data-testid='deletion-password-input']")
CONFIRM_BUTTON = (By.CSS_SELECTOR, "[data-testid='deletion-confirm-button']")
CANCEL_BUTTON = (By.CSS_SELECTOR, "[data-testid='deletion-cancel-button']")
DELETION_ERROR = (By.CSS_SELECTOR, "[data-testid='deletion-error']")
PRIMARY_CTA = (By.CSS_SELECTOR, "[data-testid='header-primary-cta-button']")

ACCESS_TOKEN_KEY = "textery.auth.accessToken"


class ProfileDeletionStatements(BaseFrontendStatements):
    """The danger zone: the only irreversible thing a user can do in this product.

    The password form is the one an account registered with email and password
    gets. Which form appears is the ACCOUNT's decision, carried by `has_password`
    on the profile -- an OAuth-only account is asked for its address instead,
    because it has no password to type.
    """

    def open_the_confirmation(self, driver: WebDriver) -> None:
        self._wait_for_visible(driver, DELETE_BUTTON).click()
        self._wait_for_visible(driver, CONFIRM_PANEL)

    def enter_the_password(self, driver: WebDriver, password: str) -> None:
        field = self._wait_for_visible(driver, PASSWORD_INPUT)
        # Select-and-delete rather than `clear()`, for the reason the name field
        # documents: `clear()` produces no key events, so React never sees it.
        field.send_keys(Keys.CONTROL, "a")
        field.send_keys(Keys.BACKSPACE)
        field.send_keys(password)

    def confirm_the_deletion(self, driver: WebDriver) -> None:
        WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(
            ec.element_to_be_clickable(CONFIRM_BUTTON),
            "the confirm button never became clickable -- the typed value did not match",
        ).click()

    def cancel_the_deletion(self, driver: WebDriver) -> None:
        self._wait_for_visible(driver, CANCEL_BUTTON).click()

    def assert_the_password_form_is_shown(self, driver: WebDriver) -> None:
        self._wait_for_visible(driver, PASSWORD_INPUT)

    def assert_the_confirm_button_is_disabled(self, driver: WebDriver) -> None:
        button = self._wait_for_visible(driver, CONFIRM_BUTTON)
        assert button.get_attribute("disabled") is not None, (
            "expected the confirm button to stay disabled until something was typed"
        )

    def assert_a_refusal_is_shown(self, driver: WebDriver) -> None:
        self._wait_for_visible(driver, DELETION_ERROR)

    def assert_the_confirmation_is_closed(self, driver: WebDriver) -> None:
        self._assert_not_visible(
            driver, CONFIRM_PANEL, "expected cancelling to close the confirmation"
        )

    def assert_the_session_ended_on_a_usable_page(self, driver: WebDriver) -> None:
        """The exit must not end in an error screen.

        The account is gone, so the very next authenticated request answers 401.
        What the user must be left with is the signed-out landing page, not a
        failure the app cannot recover from.
        """
        WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(
            lambda d: d.execute_script(
                "return window.sessionStorage.getItem(arguments[0]);", ACCESS_TOKEN_KEY
            )
            is None,
            "expected the stored session to be cleared once the account was deleted",
        )
        self._wait_for_visible(driver, PRIMARY_CTA)
