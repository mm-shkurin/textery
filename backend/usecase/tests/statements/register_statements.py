import re
from datetime import timedelta
from uuid import UUID

from scope.register_request_scope import RegisterRequestScope

from fake.auth.fake_password_hasher import FakePasswordHasher
from shared.exceptions import ConflictException
from statements.register_base import RegisterStatementsBase


class RegisterStatements(RegisterStatementsBase):
    EXPECTED_INVALID_EMAIL_ERROR_CODE = "INVALID_EMAIL"
    EXPECTED_INVALID_EMAIL_MESSAGE = "The email address is not valid."
    EXPECTED_INVALID_PASSWORD_ERROR_CODE = "INVALID_PASSWORD"
    EXPECTED_INVALID_PASSWORD_MESSAGE = "The password does not meet the password policy."
    EXPECTED_PASSWORD_MISMATCH_ERROR_CODE = "PASSWORD_MISMATCH"
    EXPECTED_PASSWORD_MISMATCH_MESSAGE = "The password confirmation does not match."
    EXPECTED_EMAIL_ALREADY_REGISTERED_ERROR_CODE = "EMAIL_ALREADY_REGISTERED"
    EXPECTED_EMAIL_ALREADY_REGISTERED_MESSAGE = "An account with this email address already exists."

    def __init__(self) -> None:
        super().__init__()
        self.returned_account = None
        self.returned_verification_code = None
        self.registered_email: str | None = None

    async def attempt_registering_with_email(self, email: str | None) -> None:
        await self._attempt_registering(RegisterRequestScope.builder(email=email))

    async def attempt_registering_with_password(self, password: str | None) -> None:
        await self._attempt_registering(
            RegisterRequestScope.builder(password=password, confirm_password=password)
        )

    async def attempt_registering_with_mismatched_confirmation(self, confirm_password: str) -> None:
        await self._attempt_registering(
            RegisterRequestScope.builder(confirm_password=confirm_password)
        )

    async def register_with_differently_normalized_password_and_confirmation(
        self, password: str, confirm_password: str
    ) -> None:
        await self._register_and_capture_result(
            RegisterRequestScope.builder(password=password, confirm_password=confirm_password)
        )

    async def attempt_registering_when_email_already_registered(self) -> None:
        self.account_repository.raise_on_save = ConflictException(
            "account with this email already exists"
        )
        await self._register_and_capture_result(RegisterRequestScope.builder())

    async def register_and_return_account(self) -> None:
        await self._register_and_capture_result(RegisterRequestScope.builder())

    async def register_with_mixed_case_email_and_return_account(self) -> None:
        await self._register_and_capture_result(
            RegisterRequestScope.builder(email="User@Example.RU")
        )

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

    def assert_account_persisted_with_server_owned_fields(self) -> None:
        self._assert_account_persisted_with_email(self.registered_email)

    def assert_account_persisted_with_normalized_email(self) -> None:
        self._assert_account_persisted_with_email("user@example.ru")

    def assert_password_hashed_from_normalized_form(
        self, expected_normalized_password: str
    ) -> None:
        """Scenario 2.7's intent, carried over to hashed storage.

        2.7 originally asserted the persisted value *was* the NFC form. Once
        hashing landed (Security 1) that became false by design, so the claim it
        actually protects is now: the hash is computed from the NFC form, never
        the raw request string -- otherwise an NFD and an NFC submission of the
        same password would produce different hashes and one of them could never
        log in.
        """
        self.assert_registration_succeeded()
        assert self.returned_account is not None, (
            "expected RegisterUser.execute to return the persisted Account"
        )
        assert self.password_hasher.hashed_values == [expected_normalized_password], (
            f"expected the hasher to receive exactly the NFC-normalized password "
            f"{[expected_normalized_password]}, got {self.password_hasher.hashed_values}"
        )
        assert self.returned_account.password_hash != expected_normalized_password, (
            "expected the persisted password_hash to be a hash, but it is the plaintext password"
        )
        expected_hash = f"{FakePasswordHasher.PREFIX}{expected_normalized_password}"
        assert self.returned_account.password_hash == expected_hash, (
            f"expected the persisted password_hash to be the hasher's output for the NFC form, "
            f"got '{self.returned_account.password_hash}'"
        )

    def _assert_account_persisted_with_email(self, expected_email: str | None) -> None:
        self.assert_registration_succeeded()
        assert self.returned_account is not None, (
            "expected RegisterUser.execute to return the persisted Account"
        )
        assert self.returned_account.email == expected_email, (
            f"expected persisted Account.email to be '{expected_email}', "
            f"got '{self.returned_account.email}'"
        )
        assert isinstance(self.returned_account.id, UUID), (
            f"expected returned Account.id to be a UUID, "
            f"got {type(self.returned_account.id).__name__}"
        )
        assert self.returned_account.is_verified is False, (
            f"expected returned Account.is_verified to be False, "
            f"got {self.returned_account.is_verified}"
        )
        assert self.returned_account.created_at == self.clock.fixed_now, (
            f"expected Account.created_at '{self.clock.fixed_now}' to come from "
            f"the injected Clock, "
            f"got '{self.returned_account.created_at}'"
        )
        assert self.account_repository.saved_accounts == [self.returned_account], (
            f"expected exactly one Account persisted via AccountRepository.save "
            f"equal to the returned Account, "
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

    async def _register_and_capture_result(self, scope: RegisterRequestScope) -> None:
        self.registered_email = scope.email
        result = await self._run_register(scope)
        if result is not None:
            self.returned_account = result.account
            self.returned_verification_code = result.verification_code

    async def _attempt_registering(self, scope: RegisterRequestScope) -> None:
        await self._run_register(scope)
