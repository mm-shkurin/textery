from datetime import UTC, datetime, timedelta

from scope.register_request_scope import RegisterRequestScope

from auth.register_user import RegisterUser
from auth.resend_code import ResendCode
from auth.verify_account import VerifyAccount
from fake.auth.fake_account_repository import FakeAccountRepository
from fake.auth.fake_clock import FakeClock
from fake.auth.fake_password_hasher import FakePasswordHasher
from fake.auth.fake_unit_of_work import FakeUnitOfWork
from fake.auth.fake_verification_code_repository import FakeVerificationCodeRepository
from shared.exceptions import ValidationException


class ResendCodeStatements:
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

    COOLDOWN_ERROR_CODE = "RESEND_COOLDOWN_ACTIVE"
    COOLDOWN_MESSAGE = "A verification code was recently sent. Please wait before requesting another."
    INVALID_OR_EXPIRED_CODE = "INVALID_OR_EXPIRED_CODE"
    INVALID_OR_EXPIRED_MESSAGE = "The verification code is invalid or has expired."

    def __init__(self) -> None:
        self.account_repository = FakeAccountRepository()
        self.password_hasher = FakePasswordHasher()
        self.clock = FakeClock(fixed_now=self.T0)
        self.verification_code_repository = FakeVerificationCodeRepository()
        self.unit_of_work = FakeUnitOfWork()
        self.registered_email: str | None = None
        self.old_code: str | None = None
        self.new_code: str | None = None
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

    def assert_rejected_as_cooldown_active_with_no_new_code(self) -> None:
        assert isinstance(self.thrown_exception, ValidationException), (
            f"expected ValidationException('{self.COOLDOWN_ERROR_CODE}'), got "
            f"{type(self.thrown_exception).__name__ if self.thrown_exception else None}: "
            f"{self.thrown_exception}"
        )
        actual = (self.thrown_exception.error_code, self.thrown_exception.message)
        expected = (self.COOLDOWN_ERROR_CODE, self.COOLDOWN_MESSAGE)
        assert actual == expected, f"expected {expected}, got {actual}"
        assert len(self.verification_code_repository.saved_codes) == self.codes_before_resend, (
            f"expected an in-cooldown resend to issue NO new code, saved_codes went from "
            f"{self.codes_before_resend} to {len(self.verification_code_repository.saved_codes)}"
        )

    def assert_new_code_issued_and_supersedes_the_old_one(self) -> None:
        assert self.thrown_exception is None, (
            f"expected a past-cooldown resend to succeed, got "
            f"{type(self.thrown_exception).__name__}: {self.thrown_exception}"
        )
        assert len(self.verification_code_repository.saved_codes) == self.codes_before_resend + 1, (
            f"expected exactly one NEW code to be persisted by the resend, saved_codes went from "
            f"{self.codes_before_resend} to {len(self.verification_code_repository.saved_codes)}"
        )
        assert self.new_code is not None and len(self.new_code) == 6 and self.new_code.isdigit(), (
            f"expected a fresh 6-digit code, got {self.new_code!r}"
        )
        assert self.new_code != self.old_code, (
            f"expected the reissued code to differ from the superseded one, both were "
            f"{self.new_code!r}"
        )
        self._assert_is_invalid_or_expired(self.old_code_verify_exception)
        assert self.new_code_verify_exception is None, (
            f"expected the NEW code to verify the account, got "
            f"{type(self.new_code_verify_exception).__name__}: {self.new_code_verify_exception}"
        )
        assert self.account_repository.saved_accounts[-1].is_verified is True, (
            "expected the account to be verified by the NEW code after supersession"
        )

    def assert_a_new_code_was_issued_at_the_boundary(self) -> None:
        assert self.thrown_exception is None, (
            f"expected a resend at exactly the 60s boundary to SUCCEED (ADR: "
            f"now - max(created_at) >= 60s), got "
            f"{type(self.thrown_exception).__name__}: {self.thrown_exception}"
        )
        assert len(self.verification_code_repository.saved_codes) == self.codes_before_resend + 1, (
            f"expected exactly one NEW code persisted at the boundary, saved_codes went from "
            f"{self.codes_before_resend} to {len(self.verification_code_repository.saved_codes)}"
        )
        assert self.new_code is not None and len(self.new_code) == 6 and self.new_code.isdigit(), (
            f"expected a fresh 6-digit code at the boundary, got {self.new_code!r}"
        )
        assert self.new_code != self.old_code, (
            f"expected the boundary-reissued code to differ from the superseded one, both were "
            f"{self.new_code!r}"
        )

    def _assert_is_invalid_or_expired(self, exc: Exception | None) -> None:
        assert isinstance(exc, ValidationException), (
            f"expected the superseded OLD code to be rejected as "
            f"ValidationException('{self.INVALID_OR_EXPIRED_CODE}'), got "
            f"{type(exc).__name__ if exc else None}: {exc}"
        )
        actual = (exc.error_code, exc.message)
        expected = (self.INVALID_OR_EXPIRED_CODE, self.INVALID_OR_EXPIRED_MESSAGE)
        assert actual == expected, f"expected {expected}, got {actual}"
