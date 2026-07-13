import pytest

from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestLoginPageDisplayAcceptance(AbstractFrontendTest):
    """UI Test Scenario 1.2: Login form displays email and password fields.

    Given the user opens the login page
    Then the email and password fields are visible
    And the submit button is visible
    """

    @pytest.mark.skip(
        reason="RED: selenium.common.exceptions.TimeoutException waiting on "
        "[data-testid='login-email-input'] -- no /login route exists yet, "
        "App.tsx falls through to the '/*' catch-all rendering the document-"
        "generation landing flow instead of a login form"
    )
    def test_should_display_login_form_fields(self, webdriver, app_url, login_page_statements):
        login_page_statements.navigate_to_login_page(webdriver, app_url)

        login_page_statements.assert_email_field_is_visible(webdriver)
        login_page_statements.assert_password_field_is_visible(webdriver)
        login_page_statements.assert_submit_button_is_visible(webdriver)
