from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestVerifyConfirmDisabledWhileInFlightAcceptance(AbstractFrontendTest):
    """UI Test Scenario 2.3a: Verify, resend, and login buttons are also
    disabled while in flight (confirm sub-case).

    Given the user has entered a code on the verify-code form
    When "Подтвердить" is clicked and the request is still in flight
    Then the confirm button is disabled

    NOTE: the spec's "a second click does not trigger a second request"
    clause is not exercised here. VerifyCodeForm.tsx has no real confirm API
    call yet (backend endpoint under parallel development), so a
    duplicate-request assertion is untestable against nothing — same scoping
    decision as Scenario 2.3's register test and 2.3a's login sub-case.
    """

    def test_should_disable_confirm_button_immediately_after_click(
        self, webdriver, app_url, verify_code_page_statements
    ):
        verify_code_page_statements.navigate_to_verify_code_page(webdriver, app_url)
        verify_code_page_statements.type_digit_into_code_input(webdriver, 0, "1")

        verify_code_page_statements.click_confirm_button(webdriver)

        verify_code_page_statements.assert_confirm_button_is_disabled(webdriver)
