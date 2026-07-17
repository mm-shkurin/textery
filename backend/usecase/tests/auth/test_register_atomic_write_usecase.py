
from statements.register_atomic_write_statements import RegisterAtomicWriteStatements


class TestRegisterUsecaseAtomicWrite:
    """Scenario 2.5: Registration writes the account and the verification code atomically.

    Given a valid registration request
    When both AccountRepository.save and VerificationCodeRepository.save succeed
    Then UnitOfWork.commit is called exactly once and UnitOfWork.rollback is never called

    Given a valid registration request
    When VerificationCodeRepository.save raises after AccountRepository.save succeeded
    Then UnitOfWork.rollback is called, UnitOfWork.commit is never called,
    and a RegistrationFailedException propagates with no raw driver/SQL detail in its message

    Given a valid registration request
    When UnitOfWork.commit itself raises after both saves succeeded
    Then UnitOfWork.rollback is called and a RegistrationFailedException propagates
    with no raw driver/SQL detail in its message
    """

    async def test_should_commit_once_and_never_rollback_when_both_saves_succeed(
        self, register_atomic_write_statements: RegisterAtomicWriteStatements
    ):
        await register_atomic_write_statements.register_with_both_saves_succeeding()
        register_atomic_write_statements.assert_commit_called_once_rollback_never()

    async def test_should_rollback_and_never_commit_when_verification_code_save_fails(
        self, register_atomic_write_statements: RegisterAtomicWriteStatements
    ):
        await register_atomic_write_statements.attempt_registering_when_verification_code_save_fails()
        register_atomic_write_statements.assert_registration_failed_error_raised(expected_saved_codes_count=0)

    async def test_should_rollback_when_final_commit_fails(
        self, register_atomic_write_statements: RegisterAtomicWriteStatements
    ):
        await register_atomic_write_statements.attempt_registering_when_final_commit_fails()
        register_atomic_write_statements.assert_registration_failed_error_raised(expected_saved_codes_count=1)

    async def test_should_rollback_and_sanitize_when_account_save_fails_with_non_conflict_error(
        self, register_atomic_write_statements: RegisterAtomicWriteStatements
    ):
        await register_atomic_write_statements.attempt_registering_when_account_save_fails_with_non_conflict_error()
        register_atomic_write_statements.assert_registration_failed_error_raised(
            expected_saved_codes_count=0, expected_saved_accounts_count=0
        )

    async def test_should_propagate_registration_failed_when_unit_of_work_is_not_injected(
        self, register_atomic_write_statements: RegisterAtomicWriteStatements
    ):
        await register_atomic_write_statements.attempt_registering_without_injected_unit_of_work()
        register_atomic_write_statements.assert_registration_failed_error_raised_without_injected_unit_of_work()

    async def test_should_propagate_registration_failed_when_rollback_itself_fails(
        self, register_atomic_write_statements: RegisterAtomicWriteStatements
    ):
        await register_atomic_write_statements.attempt_registering_when_verification_code_save_and_rollback_both_fail()
        register_atomic_write_statements.assert_registration_failed_error_raised(expected_saved_codes_count=0)
