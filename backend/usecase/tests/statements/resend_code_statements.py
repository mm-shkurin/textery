from datetime import UTC, datetime, timedelta

from scope.register_request_scope import RegisterRequestScope

from auth.register_user import RegisterUser
from auth.resend_code import ResendCode
from auth.verification_code import VerificationCode
from auth.verify_account import VerifyAccount
from fake.auth.fake_account_repository import FakeAccountRepository
from fake.auth.fake_clock import FakeClock
from fake.auth.fake_password_hasher import FakePasswordHasher
from fake.auth.fake_unit_of_work import FakeUnitOfWork
from fake.auth.fake_verification_code_repository import FakeVerificationCodeRepository
from statements.resend_code_assertions import ResendCodeAssertions


class ResendCodeStatements(ResendCodeAssertions):
    """Scenario 4.1: resend issues a new code and supersedes the previous one.

    The two behaviours the acceptance layer cannot prove (no server-clock lever):
    the 60s cooldown gate, and — once the clock is past the cooldown — that the
    reissued code supersedes the old one. Both are driven with a FakeClock.

    Arrangement goes through the real usecases, never by pre-seeding the Fakes:
    RegisterUser issues the first code, VerifyAccount is the observer that proves
    which code is active after a resend (a superseded code no longer verifies).
    """

    T0 = datetime(2026, 7, 21, 12, 0, 0, tzinfo=UTC)
    WITHIN_COOLDOWN = timedelta(seconds=30)
    AT_COOLDOWN_BOUNDARY = timedelta(seconds=60)
    PAST_COOLDOWN = timedelta(seconds=61)

    def __init__(self) -> None:
        self.account_repository = FakeAccountRepository()
        self.password_hasher = FakePasswordHasher()
        self.clock = FakeClock(fixed_now=self.T0)
        self.verification_code_repository = FakeVerificationCodeRepository()
        self.unit_of_work = FakeUnitOfWork()
        self.registered_email: str | None = None
        self.old_code: str | None = None
        self.old_code_entity: VerificationCode | None = None
        self.new_code: str | None = None
        self.returned_code: VerificationCode | None = None
        self.codes_before_resend = 0
        self.thrown_exception: Exception | None = None
        self.old_code_verify_exception: Exception | None = None
        self.new_code_verify_exception: Exception | None = None

    async def given_pending_account_with_a_code_issued_at_t0(self) -> None:
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
        self.old_code = result.verification_code.code
        self.old_code_entity = result.verification_code

    async def resend_within_the_cooldown_window(self) -> None:
        self.clock.fixed_now = self.T0 + self.WITHIN_COOLDOWN
        self.codes_before_resend = len(self.verification_code_repository.saved_codes)
        await self._execute_resend()

    async def resend_after_the_cooldown_window(self) -> None:
        await self._resend_at(self.PAST_COOLDOWN)

    async def resend_at_the_exact_cooldown_boundary(self) -> None:
        # Exactly T0 + 60s: the ADR allows a resend at `now - max(created_at) >= 60s`,
        # so this instant must SUCCEED. Pins the boundary against an off-by-one
        # green (`> 60`) that would wrongly reject a legit resend at exactly 60s.
        await self._resend_at(self.AT_COOLDOWN_BOUNDARY)

    async def resend_past_cooldown_then_again_shortly_after_the_second_code(self) -> None:
        # First resend is a legal past-cooldown resend (issues code #2). The second
        # is 30s after code #2 but ~91s after the registration code -- inside code
        # #2's cooldown. It must be REJECTED, forcing green to measure the cooldown
        # from the NEWEST code (max(created_at)), not the oldest/registration code.
        self.clock.fixed_now = self.T0 + self.PAST_COOLDOWN
        await self._execute_resend()
        self.clock.fixed_now = self.T0 + self.PAST_COOLDOWN + self.WITHIN_COOLDOWN
        self.codes_before_resend = len(self.verification_code_repository.saved_codes)
        await self._execute_resend()

    async def resend_and_capture_result(self) -> None:
        # Pull-forward for the rest route change: execute must RETURN the exact
        # VerificationCode it persisted so the HTTP 200 body carries a code that
        # actually verifies. Capture the return value (not saved_codes[-1]) so a
        # green that returns a different valid-shaped code is caught.
        self.clock.fixed_now = self.T0 + self.PAST_COOLDOWN
        self.codes_before_resend = len(self.verification_code_repository.saved_codes)
        self.returned_code = await ResendCode(
            account_repository=self.account_repository,
            verification_code_repository=self.verification_code_repository,
            clock=self.clock,
            unit_of_work=self.unit_of_work,
        ).execute(email=self.registered_email)

    async def _resend_at(self, delta: timedelta) -> None:
        self.clock.fixed_now = self.T0 + delta
        self.codes_before_resend = len(self.verification_code_repository.saved_codes)
        await self._execute_resend()
        if self.thrown_exception is None:
            self.new_code = self.verification_code_repository.saved_codes[-1].code

    async def verify_with_the_old_code_then_the_new_code(self) -> None:
        # Order matters: verify the OLD code first, while the account is still
        # pending, so a superseded code answers with the generic
        # INVALID_OR_EXPIRED_CODE (not ALREADY_VERIFIED). Then the NEW code
        # transitions the account, proving it is the active one.
        self.old_code_verify_exception = await self._execute_verify(self.old_code)
        self.new_code_verify_exception = await self._execute_verify(self.new_code)

    async def _execute_resend(self) -> None:
        try:
            await ResendCode(
                account_repository=self.account_repository,
                verification_code_repository=self.verification_code_repository,
                clock=self.clock,
                unit_of_work=self.unit_of_work,
            ).execute(email=self.registered_email)
        except Exception as exc:
            self.thrown_exception = exc

    async def _execute_verify(self, code: str | None) -> Exception | None:
        try:
            await VerifyAccount(
                account_repository=self.account_repository,
                verification_code_repository=self.verification_code_repository,
                clock=self.clock,
                unit_of_work=self.unit_of_work,
            ).execute(email=self.registered_email, code=code)
        except Exception as exc:
            return exc
        return None

