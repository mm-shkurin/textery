"""Presence and absence assertions for frontend Statements.

Split out of `base_frontend_statements.py` for the same reason `frontend_form_assertions.py` and
`request_log.py` were: to keep every file under the 200-line cap.

Both helpers here exist because the obvious one-liners are wrong in the same direction — they
pass on a page that has not finished rendering:

- `driver.find_elements(...)` + `len(...)` reads the DOM at one instant, with no wait, and counts
  hidden nodes as present. It was hand-written at six call sites across this suite.
- `ec.invisibility_of_element_located` is satisfied the moment the element is ABSENT, including
  absent because it has not been rendered YET — a free pass for an assertion whose entire content
  is absence.
"""

import time

from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait

from statements.frontend.frontend_form_assertions import WAIT_TIMEOUT_SECONDS

# How long an "is not shown" claim must keep holding before it is believed.
ABSENCE_SETTLE_SECONDS = 1.5

# Gap between re-checks during that window. This is a poll interval, not a fixed wait for a state
# to arrive (WebDriverWait uses 0.5s for the same purpose) — the assertion fails on the first
# appearance, so the interval bounds driver chatter without weakening what is being asserted.
ABSENCE_POLL_SECONDS = 0.25


class PresenceAssertionsMixin:
    """Count and absence assertions that wait, rather than sampling the DOM once."""

    @staticmethod
    def _visible_matches(driver: WebDriver, locator: tuple[str, str]) -> list[WebElement]:
        matches = []
        for element in driver.find_elements(*locator):
            try:
                if element.is_displayed():
                    matches.append(element)
            except StaleElementReferenceException:
                continue
        return matches

    def _assert_visible_element_count(
        self, driver: WebDriver, locator: tuple[str, str], expected: int, label: str
    ) -> None:
        """Assert exactly `expected` VISIBLE elements match `locator`.

        Waits for the count to be reached before asserting, so a list rendering a frame after its
        container cannot read as 0. The wait's timeout is not itself a failure — it just means the
        count never settled on the expectation, and the assertion below reports what it actually is.
        """
        try:
            WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(
                lambda d: len(self._visible_matches(d, locator)) == expected
            )
        except TimeoutException:
            pass
        actual = len(self._visible_matches(driver, locator))
        assert actual == expected, f"expected exactly {expected} visible {label}, found {actual}"

    def _assert_stays_not_visible(
        self, driver: WebDriver, locator: tuple[str, str], message: str
    ) -> None:
        """Assert `locator` is not visible now AND stays that way for the settle window.

        Use this instead of `_assert_not_visible` whenever absence IS the claim rather than a
        transition being waited out — a state that appears one frame late is then caught rather
        than missed.
        """
        deadline = time.monotonic() + ABSENCE_SETTLE_SECONDS
        while True:
            assert not self._visible_matches(driver, locator), message
            if time.monotonic() >= deadline:
                return
            time.sleep(ABSENCE_POLL_SECONDS)
