from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestRegisterDuplicateEmailErrorAcceptance(AbstractFrontendTest):
    """UI Test Scenario 5.1: Duplicate-email error displayed on registration.

    Given the user submits registration with an email that already has an account
    When the server responds with a duplicate-email error
    Then the form displays that error near the email field

    Runs against the live backend: POST /api/v1/auth/register answers 409
    EMAIL_ALREADY_REGISTERED for an email that already has an account. The test
    creates its own duplicate (see given_an_account_already_registered) rather
    than hardcoding a known-existing address, so it is self-contained and
    repeatable against the shared, never-cleaned DB.

    The expected message is the server's own text (see
    RegisterPageStatements.EXPECTED_DUPLICATE_EMAIL_MESSAGE for why it is not
    the client's to choose).
    """

    def test_should_show_duplicate_email_error_when_email_already_registered(
        self, webdriver, app_url, register_page_statements
    ):
        email = register_page_statements.given_an_account_already_registered(webdriver, app_url)

        register_page_statements.navigate_to_register_page(webdriver, app_url)
        register_page_statements.submit_registration_with_email(webdriver, email)

        register_page_statements.assert_duplicate_email_error_is_visible(webdriver)
