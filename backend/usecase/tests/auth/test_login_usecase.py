from statements.login_statements import LoginStatements


class TestLoginSuccess:
    """Scenario 6.1: valid credentials on a verified account issue a token pair."""

    async def test_should_issue_a_token_pair_for_a_verified_account(
        self, login_statements: LoginStatements
    ):
        await login_statements.given_verified_account()
        await login_statements.login_with_the_correct_password()
        login_statements.assert_token_pair_issued_for_the_account()

    async def test_should_accept_the_email_in_any_case(self, login_statements: LoginStatements):
        # Registration stores the case-folded email (scenario 2.3). Login has to
        # fold the same way or every account that signed up as "User@..." is
        # locked out of the address they typed.
        await login_statements.given_verified_account()
        await login_statements.login_with_the_email_in_a_different_case()
        login_statements.assert_token_pair_issued_for_the_account()

    async def test_should_accept_the_decomposed_form_of_the_registered_password(
        self, login_statements: LoginStatements
    ):
        # The hash was computed from the NFC form (scenario 2.7). A decomposed
        # submission is the same password to the user and a different byte string
        # to the hasher, so without normalizing here it would not verify.
        await login_statements.given_verified_account_registered_with_a_precomposed_password()
        await login_statements.login_with_the_decomposed_form_of_the_password()
        login_statements.assert_token_pair_issued_for_the_account()

    async def test_should_accept_a_stored_password_that_no_longer_satisfies_the_policy(
        self, login_statements: LoginStatements
    ):
        # Login must normalize the password, never re-validate it. Running it
        # through the Password value object would lock out every account whose
        # credential predates a policy change -- they cannot re-register.
        await login_statements.given_verified_account_whose_password_predates_the_policy()
        await login_statements.login_with_the_correct_password()
        login_statements.assert_token_pair_issued_for_the_account()


class TestLoginInvalidCredentials:
    """Scenario 5.2: invalid credentials return a single generic error.

    Every rejection below asserts the *same* error code and message. That
    sameness is the requirement: a distinct answer for an unknown email would
    enumerate which addresses are registered.
    """

    async def test_should_reject_a_wrong_password(self, login_statements: LoginStatements):
        await login_statements.given_verified_account()
        await login_statements.login_with_a_wrong_password()
        login_statements.assert_rejected_as_invalid_credentials()

    async def test_should_reject_an_unknown_email_without_revealing_it_is_unknown(
        self, login_statements: LoginStatements
    ):
        await login_statements.given_verified_account()
        await login_statements.login_with_an_unknown_email()
        login_statements.assert_rejected_as_invalid_credentials()

    async def test_should_reject_a_malformed_email_as_generic_invalid_credentials(
        self, login_statements: LoginStatements
    ):
        # Registration answers INVALID_EMAIL here; login deliberately does not.
        # A distinct code for a malformed address at login is a cheap probe for
        # which addresses the system even considers.
        await login_statements.given_verified_account()
        await login_statements.login_with_a_malformed_email()
        login_statements.assert_rejected_as_invalid_credentials()


class TestLoginUnverifiedAccount:
    """Scenario 5.1: login is rejected while the account is unverified."""

    async def test_should_reject_a_verified_password_on_a_pending_account_as_unverified(
        self, login_statements: LoginStatements
    ):
        await login_statements.given_pending_account()
        await login_statements.login_with_the_correct_password()
        login_statements.assert_rejected_as_unverified()

    async def test_should_answer_invalid_credentials_when_the_password_is_also_wrong(
        self, login_statements: LoginStatements
    ):
        # The one input where the check order is observable, and the only test
        # that pins it. Answering UNVERIFIED here would hand out account
        # existence to anyone who guessed an email and nothing else -- the
        # distinct 403 is only safe once the password is already proven correct.
        await login_statements.given_pending_account()
        await login_statements.login_with_a_wrong_password()
        login_statements.assert_rejected_as_invalid_credentials()
