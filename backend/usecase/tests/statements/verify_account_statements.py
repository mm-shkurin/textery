from datetime import datetime, timezone
from typing import Optional

from auth.register_user import RegisterUser
from auth.verify_account import VerifyAccount
from shared.exceptions import ValidationException, VerificationFailedException
from fake.auth.fake_account_repository import FakeAccountRepository
from fake.auth.fake_clock import FakeClock
from fake.auth.fake_unit_of_work import FakeUnitOfWork
from fake.auth.fake_verification_code_repository import FakeVerificationCodeRepository
from scope.register_request_scope import RegisterRequestScope


class VerifyAccountStatements:
    """Scenario 3.1: Correct code activates the account."""

    FIXED_CLOCK_NOW = datetime(2026, 7, 14, 12, 0, 0, tzinfo=timezone.utc)
    MALFORMED_CODE = "12345"
    MALFORMED_EMAIL = "not-an-email"
    UNCHANGED_BY_VERIFY_FIELDS = ("id", "email", "password_hash", "created_at")
    # Expected messages are spelled out here, not imported from the production
    # constants they pin -- importing VerifyAccount.VERIFICATION_FAILED_MESSAGE
    # would make the assertion tautological (it would pass for any edit to it).
    INVALID_CODE_MESSAGE = "The verification code is not valid."
    INVALID_EMAIL_MESSAGE = "The email address is not valid."
    VERIFICATION_FAILED_MESSAGE = (
        "Verification could not be completed due to an unexpected error. Please try again."
    )

    def __init__(self) -> None:
        self.thrown_exception: Optional[Exception] = None
        self.account_repository = FakeAccountRepository()
        self.clock = FakeClock(fixed_now=self.FIXED_CLOCK_NOW)
        self.verification_code_repository = FakeVerificationCodeRepository()
        self.unit_of_work = FakeUnitOfWork()
        self.registered_email: Optional[str] = None
        self.issued_code: Optional[str] = None
        self.original_account_snapshot = None

    async def given_pending_account_with_verification_code(self) -> None:
        scope = RegisterRequestScope.builder()
        result = await RegisterUser(
            account_repository=self.account_repository,
            clock=self.clock,
            verification_code_repository=self.verification_code_repository,
        ).execute(
            email=scope.email,
            password=scope.password,
            confirm_password=scope.confirm_password,
        )
        self.registered_email = result.account.email
        self.issued_code = result.verification_code.code
        # Snapshot field values (not the object itself) before verify() mutates
        # it in place -- FakeAccountRepository shares object identity across
        # saves/finds, so holding a reference would alias the post-verify state.
        self.original_account_snapshot = {
            field: getattr(result.account, field)
            for field in (*self.UNCHANGED_BY_VERIFY_FIELDS, "is_verified")
        }

    async def _execute_verify(self, email: str, code: str) -> None:
        try:
            await VerifyAccount(
                account_repository=self.account_repository,
                verification_code_repository=self.verification_code_repository,
                clock=self.clock,
                unit_of_work=self.unit_of_work,
            ).execute(email=email, code=code)
        except Exception as exc:
            self.thrown_exception = exc

    async def verify_with_the_issued_code(self) -> None:
        await self._execute_verify(self.registered_email, self.issued_code)

    async def verify_with_a_malformed_code(self) -> None:
        await self._execute_verify(self.registered_email, self.MALFORMED_CODE)

    async def verify_with_a_malformed_email(self) -> None:
        await self._execute_verify(self.MALFORMED_EMAIL, self.issued_code)

    async def verify_with_both_a_malformed_email_and_a_malformed_code(self) -> None:
        # The only statement that varies both axes at once. Every other one holds
        # one valid, so they all stay green under either validation order -- this
        # is what actually pins the ADR's email-first decision.
        await self._execute_verify(self.MALFORMED_EMAIL, self.MALFORMED_CODE)

    async def verify_with_the_issued_code_when_final_commit_fails(self) -> None:
        self.unit_of_work.raise_on_commit = RuntimeError("connection reset")
        await self.verify_with_the_issued_code()

    async def verify_with_the_issued_code_when_rollback_itself_fails(self) -> None:
        self.unit_of_work.raise_on_commit = RuntimeError("connection reset")
        self.unit_of_work.raise_on_rollback = RuntimeError("rollback also failed")
        await self.verify_with_the_issued_code()

    def _assert_validation_exception(self, expected_error_code: str, expected_message: str) -> None:
        assert isinstance(self.thrown_exception, ValidationException), (
            f"expected ValidationException('{expected_error_code}'), got "
            f"{type(self.thrown_exception).__name__ if self.thrown_exception else None}: "
            f"{self.thrown_exception}"
        )
        actual = (self.thrown_exception.error_code, self.thrown_exception.message)
        expected = (expected_error_code, expected_message)
        assert actual == expected, f"expected {expected}, got {actual}"

    def assert_rejected_as_invalid_code_without_touching_repositories(self) -> None:
        self._assert_validation_exception("INVALID_CODE", self.INVALID_CODE_MESSAGE)
        assert self.account_repository.find_by_email_call_count == 0, (
            f"expected a malformed code to be rejected before any account lookup, "
            f"got {self.account_repository.find_by_email_call_count} find_by_email call(s)"
        )
        assert self.verification_code_repository.find_active_by_account_id_call_count == 0, (
            f"expected a malformed code to be rejected before any verification-code lookup, got "
            f"{self.verification_code_repository.find_active_by_account_id_call_count} call(s)"
        )
        assert len(self.account_repository.saved_accounts) == 1, (
            f"expected no Account write on the malformed-code path (only the register-time "
            f"save), got {len(self.account_repository.saved_accounts)} saves"
        )

    def assert_rejected_as_invalid_email(self) -> None:
        self._assert_validation_exception("INVALID_EMAIL", self.INVALID_EMAIL_MESSAGE)

    def assert_rejected_as_invalid_email_not_invalid_code(self) -> None:
        # Pins the ADR's validation-ordering decision (email before code) against a
        # request that is bad on both axes -- the one input where the order is
        # observable at all.
        self._assert_validation_exception("INVALID_EMAIL", self.INVALID_EMAIL_MESSAGE)

    def _assert_verification_failed_with_sanitized_message(self) -> None:
        assert isinstance(self.thrown_exception, VerificationFailedException), (
            f"expected VerificationFailedException, got "
            f"{type(self.thrown_exception).__name__ if self.thrown_exception else None}: "
            f"{self.thrown_exception}"
        )
        # Exact equality is what proves sanitization: a message equal to the
        # client-safe constant cannot carry any driver/rollback failure detail.
        assert self.thrown_exception.message == self.VERIFICATION_FAILED_MESSAGE, (
            f"expected the client-safe message '{self.VERIFICATION_FAILED_MESSAGE}', "
            f"got '{self.thrown_exception.message}'"
        )
        assert str(self.thrown_exception) == self.VERIFICATION_FAILED_MESSAGE, (
            f"expected str(exception) to carry only the client-safe message, "
            f"got '{self.thrown_exception}'"
        )

    def assert_verification_failed_and_rolled_back(self) -> None:
        self._assert_verification_failed_with_sanitized_message()
        assert self.unit_of_work.rollback_call_count == 1, (
            f"expected unit_of_work.rollback() to be called exactly once on commit failure, "
            f"got {self.unit_of_work.rollback_call_count}"
        )

    def assert_verification_failed_when_rollback_also_fails(self) -> None:
        self._assert_verification_failed_with_sanitized_message()
        assert self.unit_of_work.rollback_call_count == 1, (
            f"expected unit_of_work.rollback() to be attempted exactly once even when it "
            f"raises, got {self.unit_of_work.rollback_call_count}"
        )

    def assert_account_is_verified(self) -> None:
        assert self.thrown_exception is None, (
            f"expected no exception to be raised, got "
            f"{type(self.thrown_exception).__name__}: {self.thrown_exception}"
        )
        assert len(self.account_repository.saved_accounts) == 2, (
            f"expected the Account to be saved twice (once on register, once on verify), "
            f"got {len(self.account_repository.saved_accounts)} saves"
        )
        original = self.original_account_snapshot
        verified_account = self.account_repository.saved_accounts[-1]
        actual_unchanged = {
            field: getattr(verified_account, field) for field in self.UNCHANGED_BY_VERIFY_FIELDS
        }
        expected_unchanged = {field: original[field] for field in self.UNCHANGED_BY_VERIFY_FIELDS}
        assert actual_unchanged == expected_unchanged, (
            f"expected verify to leave every field but is_verified unchanged, "
            f"got {actual_unchanged} vs original {expected_unchanged}"
        )
        assert original["is_verified"] is False, (
            f"expected the Account to be unverified immediately after registration, "
            f"got {original['is_verified']}"
        )
        assert verified_account.is_verified is True, (
            f"expected the persisted Account.is_verified to be True after verification, "
            f"got {verified_account.is_verified}"
        )
        verified_code = self.verification_code_repository.saved_codes[-1]
        assert verified_code.consumed_at == self.FIXED_CLOCK_NOW, (
            f"expected the matched VerificationCode.consumed_at to be set to the clock's "
            f"current time on successful verification, got {verified_code.consumed_at}"
        )
        assert self.unit_of_work.commit_call_count == 1, (
            f"expected unit_of_work.commit() to be called exactly once, "
            f"got {self.unit_of_work.commit_call_count}"
        )
