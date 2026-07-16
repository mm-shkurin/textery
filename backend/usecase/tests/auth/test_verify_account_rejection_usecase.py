from statements.verify_account_statements import VerifyAccountStatements


class TestVerifyAccountRejection:
    """Scenario 3.2/3.3: a code that is wrong, unknown or expired is rejected.

    All three answer with one identical generic error. That is a requirement, not
    a convenience: auth_verify.yaml's 400 must not reveal whether the email
    exists, so the unknown-account case must be indistinguishable from a wrong
    code.
    """

    async def test_should_reject_a_wrong_but_well_formed_code(
        self, verify_account_statements: VerifyAccountStatements
    ):
        await verify_account_statements.given_pending_account_with_verification_code()
        await verify_account_statements.verify_with_a_wrong_but_well_formed_code()
        verify_account_statements.assert_rejected_as_invalid_or_expired()

    async def test_should_reject_an_unknown_email_without_revealing_it_is_unknown(
        self, verify_account_statements: VerifyAccountStatements
    ):
        await verify_account_statements.given_pending_account_with_verification_code()
        await verify_account_statements.verify_with_an_unknown_email()
        verify_account_statements.assert_rejected_as_invalid_or_expired()

    async def test_should_reject_the_code_at_its_exact_expiry_instant(
        self, verify_account_statements: VerifyAccountStatements
    ):
        await verify_account_statements.given_pending_account_with_verification_code()
        await verify_account_statements.verify_with_the_issued_code_after_it_expired()
        verify_account_statements.assert_rejected_as_invalid_or_expired()
