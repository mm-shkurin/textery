from scope.register_request_scope import RegisterRequestScope

from auth.register_user import RegisterUser
from shared.exceptions import RegistrationFailedException
from statements.register_base import RegisterStatementsBase


class RegisterAtomicWriteStatements(RegisterStatementsBase):
    """Scenario 2.5: Registration writes the account and the verification code atomically."""

    EXPECTED_REGISTRATION_FAILED_MESSAGE = (
        "Registration could not be completed due to an unexpected error. Please try again."
    )
    RAW_DRIVER_ERROR_SENTINEL = "SQLSTATE 08006 connection reset by peer"

    async def register_with_both_saves_succeeding(self) -> None:
        await self._run_register(RegisterRequestScope.builder())

    async def attempt_registering_when_verification_code_save_fails(self) -> None:
        self.verification_code_repository.raise_on_save = RuntimeError(
            f"verification code insert failed: {self.RAW_DRIVER_ERROR_SENTINEL}"
        )
        await self._run_register(RegisterRequestScope.builder())

    async def attempt_registering_when_final_commit_fails(self) -> None:
        self.unit_of_work.raise_on_commit = RuntimeError(
            f"commit failed: {self.RAW_DRIVER_ERROR_SENTINEL}"
        )
        await self._run_register(RegisterRequestScope.builder())

    async def attempt_registering_when_verification_code_save_and_rollback_both_fail(self) -> None:
        self.verification_code_repository.raise_on_save = RuntimeError(
            f"verification code insert failed: {self.RAW_DRIVER_ERROR_SENTINEL}"
        )
        self.unit_of_work.raise_on_rollback = RuntimeError(
            f"rollback failed: {self.RAW_DRIVER_ERROR_SENTINEL}"
        )
        await self._run_register(RegisterRequestScope.builder())

    async def attempt_registering_when_account_save_fails_with_non_conflict_error(self) -> None:
        self.account_repository.raise_on_save = RuntimeError(
            f"account insert failed: {self.RAW_DRIVER_ERROR_SENTINEL}"
        )
        await self._run_register(RegisterRequestScope.builder())

    async def attempt_registering_without_injected_unit_of_work(self) -> None:
        """The one statement that cannot use the base's usecase builder.

        The point under test is RegisterUser's NullUnitOfWork default -- that a
        failed write still raises the sanitized error when there is no unit of
        work to roll back. Handing it the base's FakeUnitOfWork would test the
        opposite of what the name says.
        """
        self.verification_code_repository.raise_on_save = RuntimeError(
            f"verification code insert failed: {self.RAW_DRIVER_ERROR_SENTINEL}"
        )
        scope = RegisterRequestScope.builder()
        try:
            await RegisterUser(
                password_hasher=self.password_hasher,
                account_repository=self.account_repository,
                clock=self.clock,
                verification_code_repository=self.verification_code_repository,
            ).execute(
                email=scope.email,
                password=scope.password,
                confirm_password=scope.confirm_password,
            )
        except Exception as exc:
            self.thrown_exception = exc

    def assert_commit_called_once_rollback_never(self) -> None:
        assert self.thrown_exception is None, (
            f"expected no exception to be raised, got "
            f"{type(self.thrown_exception).__name__}: {self.thrown_exception}"
        )
        assert self.unit_of_work.commit_call_count == 1, (
            f"expected UnitOfWork.commit to be called exactly once, "
            f"got {self.unit_of_work.commit_call_count}"
        )
        assert self.unit_of_work.rollback_call_count == 0, (
            f"expected UnitOfWork.rollback to never be called when both saves succeed, "
            f"got {self.unit_of_work.rollback_call_count}"
        )
        assert len(self.account_repository.saved_accounts) == 1, (
            f"expected exactly one account to be saved, "
            f"got {len(self.account_repository.saved_accounts)}"
        )
        assert len(self.verification_code_repository.saved_codes) == 1, (
            f"expected exactly one verification code to be saved, "
            f"got {len(self.verification_code_repository.saved_codes)}"
        )

    def _assert_registration_failed_shape(self) -> None:
        assert isinstance(self.thrown_exception, RegistrationFailedException), (
            f"expected RegistrationFailedException to be raised, got "
            f"{type(self.thrown_exception).__name__ if self.thrown_exception else 'no exception'}"
        )
        assert self.thrown_exception.message == self.EXPECTED_REGISTRATION_FAILED_MESSAGE, (
            f"expected message '{self.EXPECTED_REGISTRATION_FAILED_MESSAGE}', "
            f"got '{self.thrown_exception.message}'"
        )
        assert self.RAW_DRIVER_ERROR_SENTINEL not in self.thrown_exception.message, (
            f"expected raised exception message to exclude raw driver/SQL detail, "
            f"got '{self.thrown_exception.message}'"
        )

    def assert_registration_failed_error_raised(
        self, expected_saved_codes_count: int, expected_saved_accounts_count: int = 1
    ) -> None:
        self._assert_registration_failed_shape()
        assert self.unit_of_work.rollback_call_count == 1, (
            f"expected UnitOfWork.rollback to be called exactly once, "
            f"got {self.unit_of_work.rollback_call_count}"
        )
        assert self.unit_of_work.commit_call_count == 0, (
            f"expected UnitOfWork.commit to never be called on this path, "
            f"got {self.unit_of_work.commit_call_count}"
        )
        assert len(self.account_repository.saved_accounts) == expected_saved_accounts_count, (
            f"expected {expected_saved_accounts_count} account(s) saved, "
            f"got {len(self.account_repository.saved_accounts)}"
        )
        assert len(self.verification_code_repository.saved_codes) == expected_saved_codes_count, (
            f"expected {expected_saved_codes_count} verification code(s) saved before rollback, "
            f"got {len(self.verification_code_repository.saved_codes)}"
        )

    def assert_registration_failed_error_raised_without_injected_unit_of_work(self) -> None:
        self._assert_registration_failed_shape()
        assert self.unit_of_work.rollback_call_count == 0, (
            f"expected the injected fake UnitOfWork (unused by this scenario) "
            f"to record no rollback calls, "
            f"got {self.unit_of_work.rollback_call_count}"
        )
        assert len(self.account_repository.saved_accounts) == 1, (
            f"expected the account save to have already succeeded before rollback, "
            f"got {len(self.account_repository.saved_accounts)}"
        )
        assert len(self.verification_code_repository.saved_codes) == 0, (
            f"expected 0 verification code(s) saved before rollback, "
            f"got {len(self.verification_code_repository.saved_codes)}"
        )
