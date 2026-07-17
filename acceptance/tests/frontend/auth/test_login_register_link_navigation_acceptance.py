from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestLoginRegisterLinkNavigationAcceptance(AbstractFrontendTest):
    """UI Test Scenario 6.2: "Don't have an account? Register" navigates to
    the registration page.

    Given the user is on the login page
    When the user clicks "Don't have an account? Register"
    Then the registration page loads
    """

    def test_should_navigate_to_register_page_when_register_link_clicked(
        self, webdriver, app_url, login_page_statements, register_page_statements
    ):
        login_page_statements.navigate_to_login_page(webdriver, app_url)

        login_page_statements.click_register_link(webdriver)

        register_page_statements.assert_url_is_register_page(webdriver, app_url)
        register_page_statements.assert_submit_button_is_visible(webdriver)
