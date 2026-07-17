import pytest

from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestVerifyCodePageDisplayAcceptance(AbstractFrontendTest):
    """UI Test Scenario 1.3: Verification-code screen displays a 6-digit input and resend action.

    Given the user has just registered and is on the verification-code screen
    Then six single-digit input boxes are visible
    And a resend action with a countdown is visible
    """

    def test_should_display_code_inputs_and_resend_action(
        self, webdriver, app_url, verify_code_page_statements
    ):
        verify_code_page_statements.navigate_to_verify_code_page(webdriver, app_url)

        verify_code_page_statements.assert_six_code_inputs_are_visible(webdriver)
        verify_code_page_statements.assert_resend_action_with_countdown_is_visible(webdriver)
