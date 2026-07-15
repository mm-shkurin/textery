import pytest

from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestRegisterSubmitLoadingIndicatorAcceptance(AbstractFrontendTest):
    """UI Test Scenario 3.1: Registration submission shows a loading state.

    Given the user has filled the registration form with valid data
    When the user submits the form
    Then a loading indicator is shown until the response arrives

    NOTE: RegisterForm.tsx currently only disables the submit button while
    in flight (Scenario 2.3) but renders no visible loading indicator
    (spinner, text change, etc.). This test targets that gap. No real
    registration API call is wired in yet (backend endpoint under parallel
    development); the in-flight window is produced by
    useSubmitPlaceholder's 500ms setTimeout placeholder, which is long
    enough for Selenium to observe the indicator before it settles.
    """

    @pytest.mark.skip(reason="RED: register-loading-indicator does not exist yet in RegisterForm.tsx")
    def test_should_show_loading_indicator_while_submission_is_in_flight(
        self, webdriver, app_url, register_page_statements
    ):
        register_page_statements.navigate_to_register_page(webdriver, app_url)
        register_page_statements.fill_registration_form(
            webdriver, "newuser@example.ru", "Password1!", "Password1!"
        )

        register_page_statements.click_submit_button(webdriver)

        register_page_statements.assert_loading_indicator_is_visible(webdriver)
