import pytest

from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestRegisterPageDisplayAcceptance(AbstractFrontendTest):
    """UI Test Scenario 1.1: Registration form displays email, password, confirm
    password fields.

    Given the user opens the registration page
    Then the email, password, and confirm password fields are visible
    And the submit button is visible
    """

    def test_should_display_registration_form_fields(self, webdriver, app_url, register_page_statements):
        register_page_statements.navigate_to_register_page(webdriver, app_url)

        register_page_statements.assert_email_field_is_visible(webdriver)
        register_page_statements.assert_password_field_is_visible(webdriver)
        register_page_statements.assert_confirm_password_field_is_visible(webdriver)
        register_page_statements.assert_submit_button_is_visible(webdriver)
