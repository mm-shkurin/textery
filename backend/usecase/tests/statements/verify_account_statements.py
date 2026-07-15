from datetime import datetime, timezone
from typing import Optional

from auth.register_user import RegisterUser
from auth.verify_account import VerifyAccount
from fake.auth.fake_account_repository import FakeAccountRepository
from fake.auth.fake_clock import FakeClock
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
            ).execute(email=self.registered_email, code=self.issued_code)
        except Exception as exc:
            self.thrown_exception = exc

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
