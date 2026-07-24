from datetime import UTC, datetime, timedelta
from uuid import UUID

from scope.register_request_scope import RegisterRequestScope

from auth.account import Account
from auth.register_user import RegisterUser
from auth.resend_code import ResendCode
from auth.verify_account import VerifyAccount
from fake.auth.fake_account_repository import FakeAccountRepository
from fake.auth.fake_clock import FakeClock
from fake.auth.fake_password_hasher import FakePasswordHasher
from fake.auth.fake_unit_of_work import FakeUnitOfWork
from fake.auth.fake_verification_code_repository import FakeVerificationCodeRepository
from shared.exceptions import ValidationException
from statements.arranged import arranged


class ResendVerifiedStatements:
    """Scenario 4.5: a resend against an ALREADY-VERIFIED account is rejected.

    The gate reuses 3.5's ALREADY_VERIFIED / "The account is already verified."
    taxonomy and sits BEFORE the cooldown check, reading the account returned by
    lock_for_update (the 4.4 post-lock re-read), not the pre-lock find_by_email one.

    Two contracts:
    (1) Ordering -- a verified account whose newest code is still inside the 60s
        cooldown answers ALREADY_VERIFIED, not RESEND_COOLDOWN_ACTIVE.
    (2) Post-lock guard -- when find_by_email returns an UNVERIFIED account but
        lock_for_update re-reads a VERIFIED one (a verify that committed inside the
        lock window), the gate must fire on the POST-lock row.

    Arrangement goes through the real usecases (RegisterUser / VerifyAccount),
    never by pre-seeding the Fakes.
    """

    T0 = datetime(2026, 7, 21, 12, 0, 0, tzinfo=UTC)
    WITHIN_COOLDOWN = timedelta(seconds=30)
    PAST_COOLDOWN = timedelta(seconds=61)
    ALREADY_VERIFIED_CODE = "ALREADY_VERIFIED"
    ALREADY_VERIFIED_MESSAGE = "The account is already verified."

    def __init__(self) -> None:
        self.account_repository = FakeAccountRepository()
        self.password_hasher = FakePasswordHasher()
        self.clock = FakeClock(fixed_now=self.T0)
        self.verification_code_repository = FakeVerificationCodeRepository()
        self.unit_of_work = FakeUnitOfWork()
        self.registered_email: str | None = None
        self.account_id: UUID | None = None
        self.thrown_exception: Exception | None = None
        self.codes_before_resend = 0

    @property
    def account_email(self) -> str:
        """The email a `given_*` step registered -- required by every act step."""
        return arranged(self.registered_email, "registered_email")

    @property
    def registered_account_id(self) -> UUID:
        return arranged(self.account_id, "account_id")

    async def given_a_verified_account_with_a_code_inside_cooldown(self) -> None:
        # Register at T0 (issues the registration code at created_at=T0), then verify
        # the account through the real VerifyAccount so is_verified flips to True. The
        # newest code stays the T0 registration code; moving the clock to T0+30s keeps
        # it INSIDE the 60s cooldown, so an un-gated execute would fall through to the
        # cooldown check -- exactly what the ordering gate must pre-empt.
        code = await self._register_at_t0()
        await VerifyAccount(
            account_repository=self.account_repository,
            verification_code_repository=self.verification_code_repository,
            clock=self.clock,
            unit_of_work=self.unit_of_work,
        ).execute(email=self.account_email, code=code)
        self.clock.fixed_now = self.T0 + self.WITHIN_COOLDOWN

    async def given_an_unverified_account_eligible_for_resend(self) -> None:
        # Register at T0 and leave the account UNVERIFIED. Push the clock past the
        # cooldown so an un-gated execute would SUCCEED (issue a fresh code) -- making
        # the RED for the post-lock guard a clean "no exception" rather than a cooldown.
        await self._register_at_t0()
        self.clock.fixed_now = self.T0 + self.PAST_COOLDOWN

    async def resend(self) -> None:
        await self._execute_resend()

    async def resend_with_the_lock_returning_a_verified_account(self) -> None:
        # premortem #2 lever: find_by_email resolves the UNVERIFIED registered account,
        # but lock_for_update RE-READS a VERIFIED account with the SAME id -- as a real
        # SELECT ... FOR UPDATE would return the freshly-committed verified row. Correct
        # wiring gates on THIS post-lock account, not the stale pre-lock one.
        verified = Account.reconstitute(
            id=self.registered_account_id,
            email=self.account_email,
            password_hash="hash",
            created_at=self.T0,
            is_verified=True,
        )
        self.account_repository.lock_for_update_override_enabled = True
        self.account_repository.lock_for_update_result = verified
        await self._execute_resend()

    async def _register_at_t0(self) -> str:
        self.clock.fixed_now = self.T0
        scope = RegisterRequestScope.builder()
        result = await RegisterUser(
            password_hasher=self.password_hasher,
            account_repository=self.account_repository,
            verification_code_repository=self.verification_code_repository,
            clock=self.clock,
        ).execute(
            email=scope.email,
            password=scope.password,
            confirm_password=scope.confirm_password,
        )
        self.registered_email = result.account.email
        self.account_id = result.account.id
        return result.verification_code.code

    async def _execute_resend(self) -> None:
        self.codes_before_resend = len(self.verification_code_repository.saved_codes)
        try:
            await ResendCode(
                account_repository=self.account_repository,
                verification_code_repository=self.verification_code_repository,
                clock=self.clock,
                unit_of_work=self.unit_of_work,
            ).execute(email=self.account_email)
        except Exception as exc:
            self.thrown_exception = exc

    def assert_rejected_as_already_verified_with_no_new_code(self) -> None:
        assert isinstance(self.thrown_exception, ValidationException), (
            f"expected ValidationException('{self.ALREADY_VERIFIED_CODE}'), got "
            f"{type(self.thrown_exception).__name__ if self.thrown_exception else None}: "
            f"{self.thrown_exception}"
        )
        actual = (self.thrown_exception.error_code, self.thrown_exception.message)
        expected = (self.ALREADY_VERIFIED_CODE, self.ALREADY_VERIFIED_MESSAGE)
        assert actual == expected, f"expected {expected}, got {actual}"
        assert len(self.verification_code_repository.saved_codes) == self.codes_before_resend, (
            f"expected a resend against a verified account to issue NO new code, saved_codes "
            f"went from {self.codes_before_resend} to "
            f"{len(self.verification_code_repository.saved_codes)}"
        )
