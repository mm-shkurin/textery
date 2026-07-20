from dataclasses import dataclass

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.wait import WebDriverWait

WAIT_TIMEOUT_SECONDS = 5

# The container each form field (label + input + inline error) is wrapped in.
# Shared across auth pages (both LoginForm.tsx and RegisterForm.tsx render it).
# Proximity assertions resolve it via Element.closest().
FIELD_CONTAINER_CLASS = "auth-field"


@dataclass(frozen=True)
class HintErrorSnapshot:
    """One element's error-display state, compared in a single assertion so a
    failure reports every wrong field at once instead of stopping at the first.
    """

    displayed: bool
    classes: tuple[str, ...]
    text: str


class FormAssertionsMixin:
    """Form-field / inline-error assertion helpers shared by the auth-page Statements.

    Split out of BaseFrontendStatements to keep both files under the 200-line limit.
    Every method resolves `self._wait_for_visible`, provided by BaseFrontendStatements,
    so this mixin is only usable when mixed into it.
    """

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

    def _assert_submit_button_visible(
        self,
        driver: WebDriver,
        locator: tuple[str, str],
        expected_text: str,
        expected_type: str | None = "submit",
    ) -> None:
        element = self._wait_for_visible(driver, locator)
        assert element.is_displayed(), "expected submit button to be visible"
        if expected_type is not None:
            assert element.get_attribute("type") == expected_type, (
                f"expected submit button type '{expected_type}', got '{element.get_attribute('type')}'"
            )
        assert element.text.strip() == expected_text, (
            f"expected submit button text '{expected_text}', got '{element.text}'"
        )

    def _assert_visible(self, driver: WebDriver, locator: tuple[str, str], label: str) -> None:
        element = self._wait_for_visible(driver, locator)
        assert element.is_displayed(), f"expected {label} to be visible"

    def _assert_hint_error_visible(
        self,
        driver: WebDriver,
        locator: tuple[str, str],
        expected_text: str,
        label: str,
        expected_classes: tuple[str, ...],
    ) -> None:
        """Asserts an inline hint-error's full display state in one compare.

        `expected_classes` is the caller's to supply — the hint-error class list
        is page-owned markup, so a shared default here would let a page that
        renders different classes silently assert another page's.
        """
        element = self._wait_for_visible(driver, locator)
        actual = HintErrorSnapshot(
            displayed=element.is_displayed(),
            classes=tuple(element.get_attribute("class").split()),
            text=element.text.strip(),
        )
        expected = HintErrorSnapshot(displayed=True, classes=expected_classes, text=expected_text)
        assert actual == expected, f"expected {label} to be {expected}, got {actual}"

    def _assert_error_shares_field_container_with_input(
        self,
        driver: WebDriver,
        error_locator: tuple[str, str],
        input_locator: tuple[str, str],
        label: str,
    ) -> None:
        """Asserts the error element sits inside the *same* field container as
        its input — i.e. it is rendered next to that field, not as a page-level
        banner that merely carries the same text.

        Proximity is asserted structurally rather than trusted from the error's
        `data-testid` name: a testid is a label the component chooses, so an
        error hoisted to the top of the page would keep passing a testid-only
        check while no longer being "near the field" the spec requires.
        """
        error = self._wait_for_visible(driver, error_locator)
        field_input = self._wait_for_visible(driver, input_locator)
        shares_container = driver.execute_script(
            "const selector = '.' + arguments[2];"
            "const errorField = arguments[0].closest(selector);"
            "return errorField !== null && errorField === arguments[1].closest(selector);",
            error,
            field_input,
            FIELD_CONTAINER_CLASS,
        )
        assert shares_container, (
            f"expected {label} to render inside the same .{FIELD_CONTAINER_CLASS} container "
            f"as its input {input_locator[1]}, but it did not"
        )

    def _assert_disabled(self, driver: WebDriver, locator: tuple[str, str], label: str) -> None:
        element = self._wait_for_visible(driver, locator)
        try:
            WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(lambda _: not element.is_enabled())
        except TimeoutException:
            pass
        assert not element.is_enabled(), f"expected {label} to be disabled"
