from pathlib import Path

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from statements.frontend.base_frontend_statements import WAIT_TIMEOUT_SECONDS, BaseFrontendStatements
from statements.frontend.profile.renderable_png import temporary_directory, write_png

FILE_INPUT = (By.CSS_SELECTOR, "[data-testid='avatar-file-input']")
DELETE_BUTTON = (By.CSS_SELECTOR, "[data-testid='avatar-delete-button']")
REJECTION = (By.CSS_SELECTOR, "[data-testid='avatar-rejection']")
PICTURE = (By.CSS_SELECTOR, "[data-testid='profile-avatar-picture']")


class ProfileAvatarStatements(BaseFrontendStatements):
    """Picking a picture, and what the page does with it.

    The file is written to disk and handed to the input with `send_keys`, which is
    the only way to drive a file picker: the dialog itself is chrome the page
    cannot reach and Selenium cannot click.
    """

    def __init__(self) -> None:
        self._directory = None

    def choose_a_photograph(self, driver: WebDriver, width: int = 900, height: int = 600) -> None:
        """A NON-SQUARE source by default -- the case a naive resize deforms."""
        self._directory = temporary_directory()
        path = write_png(Path(self._directory.name), width=width, height=height)
        # The input is deliberately not visible (the label is the control), so this is the one
        # place a locator is used without waiting for visibility.
        driver.find_element(*FILE_INPUT).send_keys(path)

    def remove_the_picture(self, driver: WebDriver) -> None:
        WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(
            ec.element_to_be_clickable(DELETE_BUTTON), "the remove button never became clickable"
        ).click()

    def assert_the_picture_is_shown(self, driver: WebDriver) -> None:
        picture = self._wait_for_visible(driver, PICTURE)
        source = picture.get_attribute("src") or ""
        assert source.startswith("blob:"), (
            "expected the image to be shown from bytes the app fetched with the token -- an "
            f"<img src> pointing at the API would be answered 401, got '{source}'"
        )

    def assert_no_picture_is_shown(self, driver: WebDriver) -> None:
        self._assert_not_visible(
            driver, PICTURE, "expected the account to show initials rather than a picture"
        )

    def assert_no_rejection_is_shown(self, driver: WebDriver) -> None:
        self._assert_not_visible(
            driver, REJECTION, "expected the upload to be accepted, but a refusal was shown"
        )

    def cleanup(self) -> None:
        if self._directory is not None:
            self._directory.cleanup()
            self._directory = None
