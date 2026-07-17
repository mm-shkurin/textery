import pytest

from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestLoginSubmitDisabledWhileInFlightAcceptance(AbstractFrontendTest):
    """UI Test Scenario 2.3a: Verify, resend, and login buttons are also
    disabled while in flight (login sub-case).

    Given the user has clicked "Log in" on the login form
    When the request is still in flight
    Then the login button is disabled

    NOTE: the spec's "a second click does not trigger a second request"
    clause is not exercised here. LoginForm.tsx has no real login API call
    yet (backend endpoint under parallel development), so a
    duplicate-request assertion is untestable against nothing — same scoping
    decision as Scenario 2.3's register test.

    NOTE: the verify-code confirm button and the resend button are not
    covered by this file. The resend button already has
    `disabled={isResending}` wired (Scenario 1.3) with no in-flight gap to
    close, so no red test is needed there. The confirm button does not
    exist yet in VerifyCodeForm.tsx at all (no button, no submit handler) —
    that is a red-frontend-first dependency (add the button and its
    in-flight state) before a red-selenium test can target it.
    """

    def test_should_disable_submit_button_immediately_after_click(
        self, webdriver, app_url, login_page_statements
    ):
        login_page_statements.navigate_to_login_page(webdriver, app_url)
        login_page_statements.fill_login_form(webdriver, "user@example.ru", "Password1!")

        login_page_statements.click_submit_button(webdriver)

        login_page_statements.assert_submit_button_is_disabled(webdriver)
