from datetime import UTC, datetime, timedelta
from uuid import uuid4

from scope.register_request_scope import RegisterRequestScope

from auth.account import Account
from auth.register_user import RegisterUser
from auth.verify_account import VerifyAccount
from fake.auth.fake_account_repository import FakeAccountRepository
from fake.auth.fake_clock import FakeClock
from fake.auth.fake_password_hasher import FakePasswordHasher
from fake.auth.fake_unit_of_work import FakeUnitOfWork
from fake.auth.fake_verification_code_repository import FakeVerificationCodeRepository
from shared.exceptions import ValidationException, VerificationFailedException


class VerifyAccountStatements:
    """Scenario 3.1: Correct code activates the account."""

    FIXED_CLOCK_NOW = datetime(2026, 7, 14, 12, 0, 0, tzinfo=UTC)
    MALFORMED_CODE = "12345"
    MALFORMED_EMAIL = "not-an-email"
    WRONG_CODE = "999999"
    UNKNOWN_EMAIL = "nobody@example.ru"
    INVALID_OR_EXPIRED_MESSAGE = "The verification code is invalid or has expired."
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
        self.thrown_exception: Exception | None = None
        self.account_repository = FakeAccountRepository()
        self.password_hasher = FakePasswordHasher()
        self.clock = FakeClock(fixed_now=self.FIXED_CLOCK_NOW)
        self.verification_code_repository = FakeVerificationCodeRepository()
        self.unit_of_work = FakeUnitOfWork()
        self.registered_email: str | None = None
        self.issued_code: str | None = None
        self.original_account_snapshot = None

    async def given_pending_account_with_verification_code(self) -> None:
        scope = RegisterRequestScope.builder()
        result = await RegisterUser(
            password_hasher=self.password_hasher,
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

    async def given_account_with_no_verification_code_ever_issued(self) -> None:
        """An account row with nothing in the code repository behind it.

        Reachable: registration writes the account and the code in that order, so
        a failure between the two -- or any later cleanup of codes -- leaves this
        state. It is the one branch in VerifyAccount that no test reached.
        """
        account = Account.create(
            id=uuid4(),
            email="user@example.ru",
            password_hash="hash",
            created_at=self.FIXED_CLOCK_NOW,
        )
        await self.account_repository.save(account)
        self.registered_email = account.email

    async def verify_an_account_that_has_no_code(self) -> None:
        await self._execute_verify(self.registered_email, "123456")

    def assert_rejected_as_invalid_or_expired_with_no_code_to_look_at(self) -> None:
        """The account exists, the lookup ran, and the answer is still generic.

        A separate assertion from `assert_rejected_as_invalid_or_expired` because
        that one requires a code to have been issued -- and the whole premise here
        is that none was. The lookup count is what pins the branch: without it the
        test would pass even if the account had not been found, which is a
        different branch that answers the same way on purpose.
        """
        self._assert_validation_exception(
            "INVALID_OR_EXPIRED_CODE", self.INVALID_OR_EXPIRED_MESSAGE
        )
        assert self.verification_code_repository.find_active_by_account_id_call_count == 1, (
            "expected the account to be found and its code looked up exactly once, got "
            f"{self.verification_code_repository.find_active_by_account_id_call_count} call(s)"
        )
        assert self.account_repository.saved_accounts[0].is_verified is False, (
            "expected the account to stay unverified"
        )
        assert self.unit_of_work.commit_call_count == 0, (
            f"expected no commit, got {self.unit_of_work.commit_call_count}"
        )

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

    async def verify_with_a_wrong_but_well_formed_code(self) -> None:
        await self._execute_verify(self.registered_email, self.WRONG_CODE)

    async def verify_with_an_unknown_email(self) -> None:
        await self._execute_verify(self.UNKNOWN_EMAIL, self.issued_code)

    async def verify_with_the_issued_code_after_it_expired(self) -> None:
        # The code expires 10 minutes after issuance; step exactly onto the expiry
        # instant, which auth_verify.yaml treats as already expired.
        self.clock.fixed_now = self.FIXED_CLOCK_NOW + timedelta(minutes=10)
        await self.verify_with_the_issued_code()

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

    def assert_rejected_as_invalid_or_expired(self) -> None:
        """One generic rejection, and no state change.

        The error code is asserted identical for a wrong code, an unknown email
        and an expired code -- that sameness is the point, since a distinct code
        (or a 500 from a None dereference) would reveal whether the email exists.
        """
        self._assert_validation_exception(
            "INVALID_OR_EXPIRED_CODE", self.INVALID_OR_EXPIRED_MESSAGE
        )
        assert len(self.account_repository.saved_accounts) == 1, (
            f"expected no Account write on a rejected verify (only the register-time save), "
            f"got {len(self.account_repository.saved_accounts)} saves"
        )
        assert self.account_repository.saved_accounts[0].is_verified is False, (
            "expected the account to stay unverified after a rejected verify"
        )
        assert len(self.verification_code_repository.saved_codes) == 1, (
            f"expected no VerificationCode write on a rejected verify, "
            f"got {len(self.verification_code_repository.saved_codes)} saves"
        )
        assert self.verification_code_repository.saved_codes[0].consumed_at is None, (
            "expected the code to stay unconsumed after a rejected verify -- a consumed "
            "code could never be retried"
        )
        assert self.unit_of_work.commit_call_count == 0, (
            f"expected no commit on a rejected verify, got {self.unit_of_work.commit_call_count}"
        )
