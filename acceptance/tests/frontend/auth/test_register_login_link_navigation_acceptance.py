import pytest

from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestRegisterLoginLinkNavigationAcceptance(AbstractFrontendTest):
    """UI Test Scenario 6.1: "Already have an account? Log in" navigates to
    the login page.

    Given the user is on the registration page
    When the user clicks "Already have an account? Log in"
    Then the login page loads
    """

    def test_should_navigate_to_login_page_when_login_link_clicked(
        self, webdriver, app_url, register_page_statements, login_page_statements
    ):
        register_page_statements.navigate_to_register_page(webdriver, app_url)

        register_page_statements.click_login_link(webdriver)

        login_page_statements.assert_url_is_login_page(webdriver, app_url)
        login_page_statements.assert_submit_button_is_visible(webdriver)
