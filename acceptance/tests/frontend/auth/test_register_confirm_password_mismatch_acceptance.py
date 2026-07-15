from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestRegisterConfirmPasswordMismatchAcceptance(AbstractFrontendTest):
    """UI Test Scenario 4.2: Password/confirm mismatch shown inline.

    Given the user has entered different values in password and confirm password
    When the user blurs the confirm-password field
    Then an inline validation message indicates the fields do not match

    NOTE: purely client-side blur validation (RegisterForm.tsx +
    frontend/src/features/auth/utils/passwordPolicy.ts), no backend
    dependency. Already implemented via red-frontend/green-frontend
    (see progress-frontend.md Scenario 4.2).
    """

    EXPECTED_MISMATCH_MESSAGE = "Пароли не совпадают"

    def test_should_show_confirm_mismatch_error_when_passwords_differ(
        self, webdriver, app_url, register_page_statements
    ):
        register_page_statements.navigate_to_register_page(webdriver, app_url)
        register_page_statements.fill_password_field(webdriver, "Str0ng!Pass")
        register_page_statements.fill_confirm_password_field(webdriver, "Different1!")

        register_page_statements.blur_confirm_password_field(webdriver)

        register_page_statements.assert_confirm_mismatch_error_is_visible(
            webdriver, self.EXPECTED_MISMATCH_MESSAGE
        )
