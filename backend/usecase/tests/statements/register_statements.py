from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from auth.register_user import RegisterUser
from fake.auth.fake_account_repository import FakeAccountRepository
from fake.auth.fake_clock import FakeClock
from scope.register_request_scope import RegisterRequestScope
from shared.exceptions import ValidationException


class RegisterStatements:
    EXPECTED_INVALID_EMAIL_ERROR_CODE = "INVALID_EMAIL"
    EXPECTED_INVALID_EMAIL_MESSAGE = "The email address is not valid."
    EXPECTED_INVALID_PASSWORD_ERROR_CODE = "INVALID_PASSWORD"
    EXPECTED_INVALID_PASSWORD_MESSAGE = "The password does not meet the password policy."
    EXPECTED_PASSWORD_MISMATCH_ERROR_CODE = "PASSWORD_MISMATCH"
    EXPECTED_PASSWORD_MISMATCH_MESSAGE = "The password confirmation does not match."
    FIXED_CLOCK_NOW = datetime(2026, 7, 14, 12, 0, 0, tzinfo=timezone.utc)

    def __init__(self) -> None:
        self.thrown_exception: Optional[Exception] = None
        self.account_repository = FakeAccountRepository()
        self.clock = FakeClock(fixed_now=self.FIXED_CLOCK_NOW)
        self.returned_account = None
        self.registered_email: Optional[str] = None

    async def attempt_registering_with_email(self, email: Optional[str]) -> None:
        await self._attempt_registering(RegisterRequestScope.builder(email=email))

    async def attempt_registering_with_password(self, password: Optional[str]) -> None:
        await self._attempt_registering(
            RegisterRequestScope.builder(password=password, confirm_password=password)
        )

    async def attempt_registering_with_mismatched_confirmation(self, confirm_password: str) -> None:
        await self._attempt_registering(
            RegisterRequestScope.builder(confirm_password=confirm_password)
        )

    async def register_and_return_account(self) -> None:
        scope = RegisterRequestScope.builder()
        self.registered_email = scope.email
        try:
            self.returned_account = await RegisterUser(
                account_repository=self.account_repository, clock=self.clock
            ).execute(
                email=scope.email,
                password=scope.password,
                confirm_password=scope.confirm_password,
            )
        except Exception as exc:
            self.thrown_exception = exc

    async def _attempt_registering(self, scope: RegisterRequestScope) -> None:
        try:
            await RegisterUser().execute(
                email=scope.email,
                password=scope.password,
                confirm_password=scope.confirm_password,
            )
        except Exception as exc:
            self.thrown_exception = exc

    def assert_invalid_email_error_raised(self) -> None:
        self._assert_validation_error_raised(
            self.EXPECTED_INVALID_EMAIL_ERROR_CODE, self.EXPECTED_INVALID_EMAIL_MESSAGE
        )

    def assert_invalid_password_error_raised(self) -> None:
        self._assert_validation_error_raised(
            self.EXPECTED_INVALID_PASSWORD_ERROR_CODE, self.EXPECTED_INVALID_PASSWORD_MESSAGE
        )

    def assert_password_mismatch_error_raised(self) -> None:
        self._assert_validation_error_raised(
            self.EXPECTED_PASSWORD_MISMATCH_ERROR_CODE, self.EXPECTED_PASSWORD_MISMATCH_MESSAGE
        )

    def assert_registration_succeeded(self) -> None:
        assert self.thrown_exception is None, (
            f"expected no exception to be raised, got "
            f"{type(self.thrown_exception).__name__}: {self.thrown_exception}"
        )

    def assert_account_persisted_with_server_owned_fields(self) -> None:
        assert self.thrown_exception is None, (
            f"expected no exception to be raised, got "
            f"{type(self.thrown_exception).__name__ if self.thrown_exception else 'no exception'}: "
            f"{self.thrown_exception}"
        )
        assert self.returned_account is not None, "expected RegisterUser.execute to return the persisted Account"
        assert self.returned_account.email == self.registered_email, (
            f"expected persisted Account.email to be '{self.registered_email}', "
            f"got '{self.returned_account.email}'"
        )
        assert isinstance(self.returned_account.id, UUID), (
            f"expected returned Account.id to be a UUID, got {type(self.returned_account.id).__name__}"
        )
        assert self.returned_account.is_verified is False, (
            f"expected returned Account.is_verified to be False, got {self.returned_account.is_verified}"
        )
        assert self.returned_account.created_at == self.clock.fixed_now, (
            f"expected Account.created_at '{self.clock.fixed_now}' to come from the injected Clock, "
            f"got '{self.returned_account.created_at}'"
        )
        assert self.account_repository.saved_accounts == [self.returned_account], (
            f"expected exactly one Account persisted via AccountRepository.save equal to the returned Account, "
            f"got {self.account_repository.saved_accounts}"
        )

    def _assert_validation_error_raised(self, expected_error_code: str, expected_message: str) -> None:
        assert isinstance(self.thrown_exception, ValidationException), (
            f"expected ValidationException to be raised, got "
            f"{type(self.thrown_exception).__name__ if self.thrown_exception else 'no exception'}"
        )
        assert self.thrown_exception.error_code == expected_error_code, (
            f"expected error_code '{expected_error_code}', "
            f"got '{self.thrown_exception.error_code}'"
        )
        assert self.thrown_exception.message == expected_message, (
            f"expected message '{expected_message}', "
            f"got '{self.thrown_exception.message}'"
        )
