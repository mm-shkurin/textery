import json
import time
from typing import ClassVar
from urllib.parse import urlparse

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

# Re-exported for the many Statements modules that import these from here; the definitions
# moved to frontend_form_assertions.py to keep both files under the 200-line limit.
from statements.frontend.frontend_form_assertions import (  # noqa: F401
    FIELD_CONTAINER_CLASS,
    WAIT_TIMEOUT_SECONDS,
    FormAssertionsMixin,
    HintErrorSnapshot,
)
from statements.frontend.live_auth_session import issue_live_session

REQUEST_LOG_SETTLE_SECONDS = 1

PRIMARY_CTA_BUTTON = (By.CSS_SELECTOR, "[data-testid='header-primary-cta-button']")
TYPE_CARD_DOKLAD = (By.CSS_SELECTOR, "[data-testid='type-card-doklad']")
MODE_CARD_AUTO = (By.CSS_SELECTOR, "[data-testid='mode-card-auto']")


class BaseFrontendStatements(FormAssertionsMixin):
    """Shared Selenium wait infrastructure for frontend Statements classes."""

    _DEFAULT_PORTS: ClassVar[dict[str, str]] = {"http": "80", "https": "443"}

    @classmethod
    def _normalized_origin(cls, url: str) -> tuple[str, str]:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        port = str(parsed.port) if parsed.port else cls._DEFAULT_PORTS.get(parsed.scheme, "")
        return parsed.scheme, f"{host}:{port}" if port else host

    def _assert_url_path(self, driver: WebDriver, app_url: str, expected_path: str) -> None:
        expected_origin = self._normalized_origin(app_url)

        def is_expected_page(d: WebDriver) -> bool:
            actual = urlparse(d.current_url)
            return (
                self._normalized_origin(d.current_url) == expected_origin
                and actual.path.rstrip("/") == expected_path
            )

        WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(
            is_expected_page, f"expected URL '{app_url}{expected_path}', got '{driver.current_url}'"
        )

    def _wait_for_visible(self, driver: WebDriver, locator: tuple[str, str]) -> WebElement:
        return WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(ec.visibility_of_element_located(locator))

    def _assert_element_text_equals(
        self, driver: WebDriver, locator: tuple[str, str], expected: str, label: str
    ) -> WebElement:
        """Wait for the element, strip its text, and assert exact equality to `expected`."""
        element = self._wait_for_visible(driver, locator)
        actual = element.text.strip()
        assert actual == expected, f"expected {label} to be '{expected}', got '{actual}'"
        return element

    # Auth-session storage keys (frontend/src/features/auth/utils/authSession.ts). The frontend
    # gates the whole type -> mode -> editor/workspace flow behind a session (Story 7, added
    # 2026-07-16): an unauthenticated CTA routes to /register, so without this the type card
    # below is never reachable and every downstream flow test times out on the CTA click.
    _ACCESS_TOKEN_KEY = "textery.auth.accessToken"
    _REFRESH_TOKEN_KEY = "textery.auth.refreshToken"

    def _establish_logged_in_precondition(
        self, driver: WebDriver, app_url: str, live_session: bool = False
    ) -> None:
        """Establish a "given a logged-in visitor" precondition in sessionStorage.

        Two grades of token, because they cost differently and the cheap one is genuinely
        sufficient for some screens:

        SEEDED (default) — a placeholder string, no backend call. Honest for a PURELY
        CLIENT-SIDE screen that makes no authenticated API call (the type and mode modals):
        `isAuthenticated()` only checks for a token's presence, and the modals render identically
        whether the token is real or seeded, because no request is sent that could reject it.

        LIVE (`live_session=True`) — a real register -> verify -> login round trip against the
        running backend. Required for any screen that calls the API on mount or submit (the
        manual editor's createDocument, the chat workspace's generation POST): a seeded token
        gets a 401, the client clears the session, and the app collapses to the landing.
        """
        driver.get(app_url)
        if live_session:
            session = issue_live_session()
            access_token, refresh_token = session.access_token, session.refresh_token
        else:
            access_token = refresh_token = "acceptance-seeded-session"
        driver.execute_script(
            "window.sessionStorage.setItem(arguments[0], arguments[2]);"
            "window.sessionStorage.setItem(arguments[1], arguments[3]);",
            self._ACCESS_TOKEN_KEY,
            self._REFRESH_TOKEN_KEY,
            access_token,
            refresh_token,
        )

    def navigate_to_doklad_type_modal(
        self, driver: WebDriver, app_url: str, live_session: bool = False
    ) -> None:
        """Navigate to the app, open the primary CTA, and select the 'doklad' type card.

        Shared entry point for both the mode-modal and chat-workspace flows, which
        diverge only in what they click next (a mode card vs. waiting on the modal).

        The type modal lives behind the Story 7 auth gate, so a logged-in precondition is
        established first. Callers whose flow ends on a screen that calls the API must pass
        `live_session=True`; see `_establish_logged_in_precondition` for the difference.
        """
        self._establish_logged_in_precondition(driver, app_url, live_session=live_session)
        driver.get(app_url)
        self._wait_for_visible(driver, PRIMARY_CTA_BUTTON).click()
        self._wait_for_visible(driver, TYPE_CARD_DOKLAD).click()

    def _count_requests_to(self, driver: WebDriver, path_substring: str, method: str = "POST") -> int:
        """Counts Network.requestWillBeSent CDP events whose URL contains
        `path_substring` and whose HTTP method matches `method` (default
        "POST" — excludes CORS preflight OPTIONS requests to the same URL).
        Requires the webdriver fixture to enable
        `goog:loggingPrefs: {"performance": "ALL"}`. Sleeps briefly first
        since CDP log delivery is asynchronous relative to the triggering
        click.
        """
        time.sleep(REQUEST_LOG_SETTLE_SECONDS)

        count = 0
        for entry in driver.get_log("performance"):
            message = json.loads(entry["message"])["message"]
            if message.get("method") != "Network.requestWillBeSent":
                continue
            request = message.get("params", {}).get("request", {})
            url = request.get("url", "")
            if path_substring in url and request.get("method") == method:
                count += 1
        return count
