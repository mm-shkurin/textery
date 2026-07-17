from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestVerifyCodeInputFocusAdvanceAcceptance(AbstractFrontendTest):
    """UI Test Scenario 2.2: Verification code input advances focus per digit.

    Given the user is on the verification-code screen with the first box focused
    When the user types a digit
    Then focus advances to the next box automatically
    """

    def test_should_advance_focus_to_next_box_when_digit_typed(
        self, webdriver, app_url, verify_code_page_statements
    ):
        verify_code_page_statements.navigate_to_verify_code_page(webdriver, app_url)

        verify_code_page_statements.type_digit_into_code_input(webdriver, 0, "1")

        verify_code_page_statements.assert_code_input_has_value(webdriver, 0, "1")
        verify_code_page_statements.assert_focus_is_on_code_input(webdriver, 1)
