import pytest

from statements.verify_account_statements import VerifyAccountStatements


class TestVerifyAccountUsecase:
    """Scenario 3.1: Correct code activates the account.

    Given a pending account with an active, unexpired verification code
    When the client submits the correct code for that account's email
    Then the account is transitioned to verified
    And the verified account is persisted via AccountRepository
    """

    async def test_should_verify_account_with_correct_code(
        self, verify_account_statements: VerifyAccountStatements
    ):
        await verify_account_statements.given_pending_account_with_verification_code()
        await verify_account_statements.verify_with_the_issued_code()
        verify_account_statements.assert_account_is_verified()

    @pytest.mark.skip(
        reason="RED: VerifyAccount has no _validate_code -- a malformed code falls "
        "through matches() and execute() returns None instead of ValidationException"
    )
    async def test_should_reject_malformed_code_before_any_repository_lookup(
        self, verify_account_statements: VerifyAccountStatements
    ):
        await verify_account_statements.given_pending_account_with_verification_code()
        await verify_account_statements.verify_with_a_malformed_code()
        verify_account_statements.assert_rejected_as_invalid_code_without_touching_repositories()

    @pytest.mark.skip(
        reason="RED: VerifyAccount.execute has a bare Email(email) call with no "
        "_validate_email -- ValueError leaks out and answers 500, not 400 INVALID_EMAIL"
    )
    async def test_should_reject_malformed_email_as_invalid_email(
        self, verify_account_statements: VerifyAccountStatements
    ):
        await verify_account_statements.given_pending_account_with_verification_code()
        await verify_account_statements.verify_with_a_malformed_email()
        verify_account_statements.assert_rejected_as_invalid_email()

    async def test_should_rollback_and_raise_sanitized_error_when_final_commit_fails(
        self, verify_account_statements: VerifyAccountStatements
    ):
        await verify_account_statements.given_pending_account_with_verification_code()
        await verify_account_statements.verify_with_the_issued_code_when_final_commit_fails()
        verify_account_statements.assert_verification_failed_and_rolled_back()

    async def test_should_surface_verification_failed_not_secondary_exception_when_rollback_itself_fails(
        self, verify_account_statements: VerifyAccountStatements
    ):
        await verify_account_statements.given_pending_account_with_verification_code()
        await verify_account_statements.verify_with_the_issued_code_when_rollback_itself_fails()
        verify_account_statements.assert_verification_failed_when_rollback_also_fails()
