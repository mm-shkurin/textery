from datetime import datetime, timezone
from typing import Optional

from auth.register_user import RegisterUser
from auth.verify_account import VerifyAccount
from shared.exceptions import VerificationFailedException
from fake.auth.fake_account_repository import FakeAccountRepository
from fake.auth.fake_clock import FakeClock
from fake.auth.fake_unit_of_work import FakeUnitOfWork
from fake.auth.fake_verification_code_repository import FakeVerificationCodeRepository
from scope.register_request_scope import RegisterRequestScope


class VerifyAccountStatements:
    """Scenario 3.1: Correct code activates the account."""

    FIXED_CLOCK_NOW = datetime(2026, 7, 14, 12, 0, 0, tzinfo=timezone.utc)

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
            "id": result.account.id,
            "email": result.account.email,
            "password_hash": result.account.password_hash,
            "created_at": result.account.created_at,
            "is_verified": result.account.is_verified,
        }

    async def verify_with_the_issued_code(self) -> None:
        try:
            await VerifyAccount(
                account_repository=self.account_repository,
                verification_code_repository=self.verification_code_repository,
                clock=self.clock,
                unit_of_work=self.unit_of_work,
            ).execute(email=self.registered_email, code=self.issued_code)
        except Exception as exc:
            self.thrown_exception = exc

    async def verify_with_the_issued_code_when_final_commit_fails(self) -> None:
        self.unit_of_work.raise_on_commit = RuntimeError("connection reset")
        await self.verify_with_the_issued_code()

    async def verify_with_the_issued_code_when_rollback_itself_fails(self) -> None:
        self.unit_of_work.raise_on_commit = RuntimeError("connection reset")
        self.unit_of_work.raise_on_rollback = RuntimeError("rollback also failed")
        await self.verify_with_the_issued_code()

    def assert_verification_failed_and_rolled_back(self) -> None:
        assert isinstance(self.thrown_exception, VerificationFailedException), (
            f"expected VerificationFailedException, got "
            f"{type(self.thrown_exception).__name__ if self.thrown_exception else None}"
        )
        assert "connection reset" not in str(self.thrown_exception), (
            "expected the raw driver/commit failure detail to be sanitized out of the "
            f"raised exception message, got: {self.thrown_exception}"
        )
        assert self.unit_of_work.rollback_call_count == 1, (
            f"expected unit_of_work.rollback() to be called exactly once on commit failure, "
            f"got {self.unit_of_work.rollback_call_count}"
        )

    def assert_verification_failed_when_rollback_also_fails(self) -> None:
        assert isinstance(self.thrown_exception, VerificationFailedException), (
            f"expected VerificationFailedException (not the secondary rollback exception) to "
            f"surface, got {type(self.thrown_exception).__name__ if self.thrown_exception else None}"
        )
        assert "rollback also failed" not in str(self.thrown_exception), (
            f"expected the secondary rollback exception to be swallowed, not surfaced, "
            f"got: {self.thrown_exception}"
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
        assert verified_account.id == original["id"], (
            f"expected the same Account.id to be re-persisted on verify, "
            f"got '{verified_account.id}' vs original '{original['id']}'"
        )
        assert verified_account.email == original["email"], (
            f"expected Account.email to be unchanged by verify, "
            f"got '{verified_account.email}' vs original '{original['email']}'"
        )
        assert verified_account.password_hash == original["password_hash"], (
            f"expected Account.password_hash to be unchanged by verify, "
            f"got '{verified_account.password_hash}' vs original '{original['password_hash']}'"
        )
        assert verified_account.created_at == original["created_at"], (
            f"expected Account.created_at to be unchanged by verify, "
            f"got '{verified_account.created_at}' vs original '{original['created_at']}'"
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
