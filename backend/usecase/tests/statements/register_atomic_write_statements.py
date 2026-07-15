from datetime import datetime, timezone
from typing import Optional

from auth.register_user import RegisterUser
from fake.auth.fake_account_repository import FakeAccountRepository
from fake.auth.fake_clock import FakeClock
from fake.auth.fake_unit_of_work import FakeUnitOfWork
from fake.auth.fake_verification_code_repository import FakeVerificationCodeRepository
from scope.register_request_scope import RegisterRequestScope
from shared.exceptions import RegistrationFailedException


class RegisterAtomicWriteStatements:
    """Scenario 2.5: Registration writes the account and the verification code atomically."""

    EXPECTED_REGISTRATION_FAILED_MESSAGE = (
        "Registration could not be completed due to an unexpected error. Please try again."
    )
    RAW_DRIVER_ERROR_SENTINEL = "SQLSTATE 08006 connection reset by peer"
    FIXED_CLOCK_NOW = datetime(2026, 7, 14, 12, 0, 0, tzinfo=timezone.utc)

    def __init__(self) -> None:
        self.thrown_exception: Optional[Exception] = None
        self.account_repository = FakeAccountRepository()
        self.clock = FakeClock(fixed_now=self.FIXED_CLOCK_NOW)
        self.verification_code_repository = FakeVerificationCodeRepository()
        self.unit_of_work = FakeUnitOfWork()

    async def register_with_both_saves_succeeding(self) -> None:
        await self._execute_register()

    async def attempt_registering_when_verification_code_save_fails(self) -> None:
        self.verification_code_repository.raise_on_save = RuntimeError(
            f"verification code insert failed: {self.RAW_DRIVER_ERROR_SENTINEL}"
        )
        await self._execute_register()

    async def attempt_registering_when_final_commit_fails(self) -> None:
        self.unit_of_work.raise_on_commit = RuntimeError(
            f"commit failed: {self.RAW_DRIVER_ERROR_SENTINEL}"
        )
        await self._execute_register()

    async def _execute_register(self) -> None:
        scope = RegisterRequestScope.builder()
        try:
            await RegisterUser(
                account_repository=self.account_repository,
                clock=self.clock,
                verification_code_repository=self.verification_code_repository,
                unit_of_work=self.unit_of_work,
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

    def assert_registration_failed_error_raised(self) -> None:
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
        assert self.unit_of_work.rollback_call_count == 1, (
            f"expected UnitOfWork.rollback to be called exactly once, "
            f"got {self.unit_of_work.rollback_call_count}"
        )
        assert self.unit_of_work.commit_call_count == 0, (
            f"expected UnitOfWork.commit to never be called on this path, "
            f"got {self.unit_of_work.commit_call_count}"
        )
        assert len(self.account_repository.saved_accounts) == 1, (
            f"expected the account save to have already succeeded before rollback, "
            f"got {len(self.account_repository.saved_accounts)}"
        )
