from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.wait import WebDriverWait

from statements.frontend.base_frontend_statements import WAIT_TIMEOUT_SECONDS, BaseFrontendStatements

THEME_TOGGLE = (By.CSS_SELECTOR, "[data-testid='profile-theme-toggle']")
PROFILE_MENU = (By.CSS_SELECTOR, "[data-testid='profile-profile-menu']")

THEME_ATTRIBUTE = "data-theme"


class ProfileThemeStatements(BaseFrontendStatements):
    """The theme switch in the account menu, and whether the choice survives a reload.

    The assertion is on `<html data-theme>` rather than on a colour: the attribute
    is what every token in the stylesheet keys off, and asserting a computed colour
    would tie the test to the palette instead of to the switch.
    """

    def read_theme(self, driver: WebDriver) -> str:
        return driver.execute_script(
            "return document.documentElement.getAttribute(arguments[0]);", THEME_ATTRIBUTE
        )

    def toggle_the_theme(self, driver: WebDriver) -> None:
        self._wait_for_visible(driver, THEME_TOGGLE).click()

    def assert_the_menu_stayed_open(self, driver: WebDriver) -> None:
        """Unlike the two items that navigate away, this one changes the page underneath.

        Closing the panel would hide the result of the click behind the click's own
        side effect.
        """
        self._wait_for_visible(driver, PROFILE_MENU)

    def assert_the_theme_is(self, driver: WebDriver, expected: str) -> None:
        WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(
            lambda d: self.read_theme(d) == expected,
            f"expected <html {THEME_ATTRIBUTE}='{expected}', got '{self.read_theme(driver)}'",
        )

    def reload(self, driver: WebDriver) -> None:
        driver.refresh()
