from statements.verify_account_already_verified_statements import (
    VerifyAccountAlreadyVerifiedStatements,
)


class TestVerifyAccountAlreadyVerifiedRejection:
    """Scenario 3.5: verify against an already-verified account is rejected.

    Given an account already verified once with its issued code
    When a DIFFERENT valid 6-digit code is submitted for the same email
    Then execute raises ValidationException(ALREADY_VERIFIED) AND nothing is
    persisted -- no Account save, no VerificationCode save, no commit.
    """

    async def test_should_reject_non_matching_code_on_verified_account(
        self,
        verify_account_already_verified_statements: VerifyAccountAlreadyVerifiedStatements,
    ):
        statements = verify_account_already_verified_statements
        await statements.given_account_already_verified_once_with_its_code()
        await statements.submit_a_different_code_against_the_verified_account()
        statements.assert_rejected_as_already_verified_without_persisting()
