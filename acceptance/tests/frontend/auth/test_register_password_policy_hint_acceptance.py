from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestRegisterPasswordPolicyHintAcceptance(AbstractFrontendTest):
    """UI Test Scenario 4.1: Password policy hint shown inline.

    Given the user is on the registration page
    When the user types a non-compliant password and blurs the field
    Then an inline error message describing the password policy is shown

    NOTE: purely client-side blur validation (RegisterForm.tsx +
    frontend/src/features/auth/utils/passwordPolicy.ts), no backend
    dependency. Already implemented via red-frontend/green-frontend
    (see progress-frontend.md Scenario 4.1).
    """

    EXPECTED_POLICY_HINT = (
        "Минимум 8 символов, включая цифру, заглавную, строчную буквы и спецсимвол"
    )

    def test_should_show_password_policy_error_when_password_is_non_compliant(
        self, webdriver, app_url, register_page_statements
    ):
        register_page_statements.navigate_to_register_page(webdriver, app_url)
        register_page_statements.fill_password_field(webdriver, "weak")

        register_page_statements.blur_password_field(webdriver)

        register_page_statements.assert_password_policy_error_is_visible(
            webdriver, self.EXPECTED_POLICY_HINT
        )
