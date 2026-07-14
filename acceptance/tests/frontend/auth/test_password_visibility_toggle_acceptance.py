import pytest

from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestPasswordVisibilityToggleAcceptance(AbstractFrontendTest):
    """UI Test Scenario 2.1: Password field visibility toggle.

    Given the user is on the login form with the password field masked
    When the user clicks the show-password toggle
    Then the password field displays its plain-text value
    """

    @pytest.mark.skip(reason="RED: no show-password toggle in LoginForm.tsx yet")
    def test_should_reveal_password_when_toggle_clicked(self, webdriver, app_url, login_page_statements):
        login_page_statements.navigate_to_login_page(webdriver, app_url)

        login_page_statements.assert_password_field_is_masked(webdriver)

        login_page_statements.click_show_password_toggle(webdriver)

        login_page_statements.assert_password_field_is_plain_text(webdriver)
