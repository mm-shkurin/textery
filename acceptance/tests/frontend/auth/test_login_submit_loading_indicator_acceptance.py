import pytest

from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestLoginSubmitLoadingIndicatorAcceptance(AbstractFrontendTest):
    """UI Test Scenario 3.2: Login submission shows a loading state.

    Given the user has filled the login form with valid credentials
    When the user submits the form
    Then a loading indicator is shown until the response arrives

    NOTE: LoginForm.tsx still uses useSubmitPlaceholder (a pure client-side
    500ms setTimeout), unlike RegisterForm which Scenario 5.1 wired to a
    real registerApi.register call. No real login API call exists yet, so
    the in-flight window is long enough for Selenium to observe the
    indicator before it settles.
    """

    def test_should_show_loading_indicator_while_submission_is_in_flight(
        self, webdriver, app_url, login_page_statements
    ):
        login_page_statements.navigate_to_login_page(webdriver, app_url)
        login_page_statements.fill_login_form(webdriver, "user@example.ru", "Password1!")

        login_page_statements.click_submit_button(webdriver)

        login_page_statements.assert_loading_indicator_is_visible(webdriver)
