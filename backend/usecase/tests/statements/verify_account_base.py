from datetime import UTC, datetime

from scope.register_request_scope import RegisterRequestScope

from auth.register_user import RegisterUser
from auth.verify_account import VerifyAccount
from fake.auth.fake_account_repository import FakeAccountRepository
from fake.auth.fake_clock import FakeClock
from fake.auth.fake_password_hasher import FakePasswordHasher
from fake.auth.fake_unit_of_work import FakeUnitOfWork
from fake.auth.fake_verification_code_repository import FakeVerificationCodeRepository
from shared.exceptions import ValidationException
from statements.arranged import arranged


class VerifyAccountStatementsBase:
    """The wiring both verify-account statements classes need: the same fakes, the
    same registered-account arrangement, and the same way of running the usecase.

    Split out because the single class had grown past the project's 200-line file
    limit while covering two unrelated concerns -- what /verify answers for a bad
    request, and what it does when the write itself fails. Those are separate
    files now (the split `register_atomic_write_statements` already makes for the
    register flow), and this is the part that would otherwise be copied into both.

    A base class rather than a helper module because the arrangement *is* shared
    mutable state -- the fakes and the snapshot -- which a function would have to
    hand back as a bag and every caller unpack.
    """

    FIXED_CLOCK_NOW = datetime(2026, 7, 14, 12, 0, 0, tzinfo=UTC)
    UNCHANGED_BY_VERIFY_FIELDS = ("id", "email", "password_hash", "created_at")
    # Expected messages are spelled out here, not imported from the production
    # constants they pin -- importing VerifyAccount.VERIFICATION_FAILED_MESSAGE
    # would make the assertion tautological (it would pass for any edit to it).
    INVALID_EMAIL_MESSAGE = "The email address is not valid."

    def __init__(self) -> None:
        self.thrown_exception: Exception | None = None
        self.account_repository = FakeAccountRepository()
        self.password_hasher = FakePasswordHasher()
        self.clock = FakeClock(fixed_now=self.FIXED_CLOCK_NOW)
        self.verification_code_repository = FakeVerificationCodeRepository()
        self.unit_of_work = FakeUnitOfWork()
        self.registered_email: str | None = None
        self.issued_code: str | None = None
        self.original_account_snapshot: dict[str, object] | None = None
        self.account_saves_after_first_verify = 0
        self.code_saves_after_first_verify = 0
        self.commits_after_first_verify = 0

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

    async def given_account_already_verified_once_with_its_code(self) -> None:
        """Register a pending account, verify it once with its issued code, then
        snapshot the persist/commit counts left by that first verify. Both the
        already-verified rejection (3.5) and the idempotent replay (3.4) build on
        this same arrangement; each subclass adds only its own extra snapshot.
        """
        await self.given_pending_account_with_verification_code()
        await self._execute_verify(self.account_email, self.account_code)
        self.account_saves_after_first_verify = len(self.account_repository.saved_accounts)
        self.code_saves_after_first_verify = len(self.verification_code_repository.saved_codes)
        self.commits_after_first_verify = self.unit_of_work.commit_call_count

    @property
    def account_email(self) -> str:
        """The email a `given_*` step registered -- required by every act step."""
        return arranged(self.registered_email, "registered_email")

    @property
    def account_code(self) -> str:
        return arranged(self.issued_code, "issued_code")

    @property
    def account_snapshot(self) -> dict[str, object]:
        return arranged(self.original_account_snapshot, "original_account_snapshot")

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

    def _assert_validation_exception(self, expected_error_code: str, expected_message: str) -> None:
        assert isinstance(self.thrown_exception, ValidationException), (
            f"expected ValidationException('{expected_error_code}'), got "
            f"{type(self.thrown_exception).__name__ if self.thrown_exception else None}: "
            f"{self.thrown_exception}"
        )
        actual = (self.thrown_exception.error_code, self.thrown_exception.message)
        expected = (expected_error_code, expected_message)
        assert actual == expected, f"expected {expected}, got {actual}"
