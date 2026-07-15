import re
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from auth.register_user import RegisterUser
from fake.auth.fake_account_repository import FakeAccountRepository
from fake.auth.fake_clock import FakeClock
from fake.auth.fake_verification_code_repository import FakeVerificationCodeRepository
from scope.register_request_scope import RegisterRequestScope
from shared.exceptions import ConflictException, ValidationException


class RegisterStatements:
    EXPECTED_INVALID_EMAIL_ERROR_CODE = "INVALID_EMAIL"
    EXPECTED_INVALID_EMAIL_MESSAGE = "The email address is not valid."
    EXPECTED_INVALID_PASSWORD_ERROR_CODE = "INVALID_PASSWORD"
    EXPECTED_INVALID_PASSWORD_MESSAGE = "The password does not meet the password policy."
    EXPECTED_PASSWORD_MISMATCH_ERROR_CODE = "PASSWORD_MISMATCH"
    EXPECTED_PASSWORD_MISMATCH_MESSAGE = "The password confirmation does not match."
    EXPECTED_EMAIL_ALREADY_REGISTERED_ERROR_CODE = "EMAIL_ALREADY_REGISTERED"
    EXPECTED_EMAIL_ALREADY_REGISTERED_MESSAGE = "An account with this email address already exists."
    FIXED_CLOCK_NOW = datetime(2026, 7, 14, 12, 0, 0, tzinfo=timezone.utc)

    def __init__(self) -> None:
        self.thrown_exception: Optional[Exception] = None
        self.account_repository = FakeAccountRepository()
        self.clock = FakeClock(fixed_now=self.FIXED_CLOCK_NOW)
        self.verification_code_repository = FakeVerificationCodeRepository()
        self.returned_account = None
        self.returned_verification_code = None
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

    async def attempt_registering_when_email_already_registered(self) -> None:
        self.account_repository.raise_on_save = ConflictException(
            "account with this email already exists"
        )
        await self._execute_register(RegisterRequestScope.builder())

    async def register_and_return_account(self) -> None:
        scope = RegisterRequestScope.builder()
        self.registered_email = scope.email
        result = await self._execute_register(scope)
        if result is not None:
            self.returned_account = result.account
            self.returned_verification_code = result.verification_code

    async def _execute_register(self, scope: RegisterRequestScope):
        try:
            return await RegisterUser(
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
            return None

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

    def assert_email_already_registered_error_raised(self) -> None:
        self._assert_validation_error_raised(
            self.EXPECTED_EMAIL_ALREADY_REGISTERED_ERROR_CODE,
            self.EXPECTED_EMAIL_ALREADY_REGISTERED_MESSAGE,
        )
        assert self.verification_code_repository.saved_codes == [], (
            f"expected no VerificationCode to be persisted when registration is rejected "
            f"for a duplicate email, got {self.verification_code_repository.saved_codes}"
        )
        assert self.account_repository.saved_accounts == [], (
            f"expected no Account to be persisted when registration is rejected "
            f"for a duplicate email, got {self.account_repository.saved_accounts}"
        )

    def assert_registration_succeeded(self) -> None:
        assert self.thrown_exception is None, (
            f"expected no exception to be raised, got "
            f"{type(self.thrown_exception).__name__}: {self.thrown_exception}"
        )

    def assert_account_persisted_with_server_owned_fields(self) -> None:
        self.assert_registration_succeeded()
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

    def assert_verification_code_issued(self) -> None:
        self.assert_registration_succeeded()
        assert self.returned_account is not None, (
            "expected RegisterUser.execute to return the persisted Account"
        )
        assert self.returned_verification_code is not None, (
            "expected RegisterUser.execute to return a VerificationCode"
        )
        assert isinstance(self.returned_verification_code.id, UUID), (
            f"expected VerificationCode.id to be a UUID, "
            f"got {type(self.returned_verification_code.id).__name__}"
        )
        assert re.fullmatch(r"\d{6}", self.returned_verification_code.code), (
            f"expected VerificationCode.code to be a 6-digit zero-padded string, "
            f"got '{self.returned_verification_code.code}'"
        )
        expected_expires_at = self.clock.fixed_now + timedelta(minutes=10)
        assert self.returned_verification_code.expires_at == expected_expires_at, (
            f"expected VerificationCode.expires_at to be '{expected_expires_at}' "
            f"(clock.now() + 10 minutes), got '{self.returned_verification_code.expires_at}'"
        )
        assert self.returned_verification_code.account_id == self.returned_account.id, (
            f"expected VerificationCode.account_id to be '{self.returned_account.id}', "
            f"got '{self.returned_verification_code.account_id}'"
        )
        assert self.verification_code_repository.saved_codes == [self.returned_verification_code], (
            f"expected exactly one VerificationCode persisted via VerificationCodeRepository.save "
            f"equal to the returned VerificationCode, "
            f"got {self.verification_code_repository.saved_codes}"
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
