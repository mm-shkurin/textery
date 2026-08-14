from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from statements.frontend.base_frontend_statements import WAIT_TIMEOUT_SECONDS, BaseFrontendStatements
from statements.frontend.live_auth_session import issue_live_session

HEADER_PROFILE_BUTTON = (By.CSS_SELECTOR, "[data-testid='header-profile-button']")
HEADER_PROFILE_LINK = (By.CSS_SELECTOR, "[data-testid='header-profile-link']")
PROFILE_SCREEN = (By.CSS_SELECTOR, "[data-testid='profile-screen']")
PROFILE_BUTTON = (By.CSS_SELECTOR, "[data-testid='profile-profile-button']")
PROFILE_EMAIL = (By.CSS_SELECTOR, "[data-testid='profile-profile-email']")
NAME_INPUT = (By.CSS_SELECTOR, "[data-testid='profile-name-input']")
NAME_SAVE = (By.CSS_SELECTOR, "[data-testid='profile-name-save']")
NAME_COUNTER = (By.CSS_SELECTOR, "[data-testid='profile-name-counter']")
IDENTITY_PRIMARY = (By.CSS_SELECTOR, "[data-testid='profile-identity-primary']")


class ProfilePageStatements(BaseFrontendStatements):
    """Reaching the profile screen, and the display-name form on it.

    Navigation is by clicking, never by typing `/profile`: the account menu in the
    header is how a user gets there, and a test that jumped straight to the URL
    would keep passing after the only link to the screen disappeared.
    """

    def __init__(self) -> None:
        self.session = None

    def navigate_to_profile_page(self, driver: WebDriver, app_url: str) -> None:
        # A LIVE session, not a seeded token: this screen calls `GET /me` on mount, and a fake
        # token would be answered 401.
        self.session = issue_live_session()
        driver.get(app_url)
        driver.execute_script(
            "window.sessionStorage.setItem(arguments[0], arguments[2]);"
            "window.sessionStorage.setItem(arguments[1], arguments[3]);",
            self._ACCESS_TOKEN_KEY,
            self._REFRESH_TOKEN_KEY,
            self.session.access_token,
            self.session.refresh_token,
        )
        driver.get(app_url)
        self._wait_for_visible(driver, HEADER_PROFILE_BUTTON).click()
        self._wait_for_visible(driver, HEADER_PROFILE_LINK).click()
        self._wait_for_visible(driver, PROFILE_SCREEN)

    @property
    def account_email(self) -> str:
        assert self.session is not None, "navigate_to_profile_page has not run yet"
        return self.session.email

    @property
    def account_password(self) -> str:
        assert self.session is not None, "navigate_to_profile_page has not run yet"
        return self.session.password

    def enter_name(self, driver: WebDriver, name: str) -> None:
        self.clear_the_name_field(driver)
        self._wait_for_visible(driver, NAME_INPUT).send_keys(name)

    def clear_the_name_field(self, driver: WebDriver) -> None:
        """Select everything and delete it, rather than calling `clear()`.

        `WebElement.clear()` empties the DOM value without producing the key
        events React listens to, so the component's state keeps the old value and
        the save button stays disabled over a field that LOOKS empty. Selecting
        and deleting is also what a person does.
        """
        field = self._wait_for_visible(driver, NAME_INPUT)
        field.send_keys(Keys.CONTROL, "a")
        field.send_keys(Keys.BACKSPACE)

    def save_the_name(self, driver: WebDriver) -> None:
        button = WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(
            ec.element_to_be_clickable(NAME_SAVE), "the save button never became clickable"
        )
        button.click()

    def open_the_account_menu(self, driver: WebDriver) -> None:
        self._wait_for_visible(driver, PROFILE_BUTTON).click()

    def assert_the_header_shows(self, driver: WebDriver, expected: str) -> None:
        """The account menu's identity row, WITHOUT a page reload.

        The whole point of answering a rename with the full profile is that the
        header updates from that response. A test that reloaded first would pass
        against a client that only ever learns the new name from a fresh GET.
        """
        self.open_the_account_menu(driver)
        WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(
            ec.text_to_be_present_in_element(PROFILE_EMAIL, expected),
            f"expected the account menu to show '{expected}', got "
            f"'{self._wait_for_visible(driver, PROFILE_EMAIL).text}'",
        )

    def assert_the_screen_shows_the_name(self, driver: WebDriver, expected: str) -> None:
        WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(
            ec.text_to_be_present_in_element(IDENTITY_PRIMARY, expected),
            f"expected the profile card to show '{expected}'",
        )

    def assert_the_name_field_holds(self, driver: WebDriver, expected: str) -> None:
        WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(
            lambda d: self._wait_for_visible(d, NAME_INPUT).get_attribute("value") == expected,
            f"expected the name field to hold '{expected}', got "
            f"'{self._wait_for_visible(driver, NAME_INPUT).get_attribute('value')}'",
        )

    def assert_the_counter_reads(self, driver: WebDriver, expected: str) -> None:
        self._assert_element_text_equals(driver, NAME_COUNTER, expected, "the name counter")

    def assert_the_save_button_is_disabled(self, driver: WebDriver) -> None:
        button = self._wait_for_visible(driver, NAME_SAVE)
        assert button.get_attribute("disabled") is not None, (
            "expected the save button to be disabled when there is nothing to send"
        )
