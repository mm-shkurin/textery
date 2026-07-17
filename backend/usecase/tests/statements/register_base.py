from datetime import UTC, datetime

from scope.register_request_scope import RegisterRequestScope

from auth.register_user import RegisterUser
from fake.auth.fake_account_repository import FakeAccountRepository
from fake.auth.fake_clock import FakeClock
from fake.auth.fake_password_hasher import FakePasswordHasher
from fake.auth.fake_unit_of_work import FakeUnitOfWork
from fake.auth.fake_verification_code_repository import FakeVerificationCodeRepository
from shared.exceptions import ValidationException


class RegisterStatementsBase:
    """The arrangement every register-flow statements class needs.

    RegisterStatements and RegisterAtomicWriteStatements had byte-identical
    __init__ bodies -- the same five fakes and the same frozen clock -- because
    they were written as separate scenario classes and the setup came along for
    the ride. One copy now, so a change to the fake wiring cannot land in one and
    miss the other.

    A base class rather than a helper function because what is shared is mutable
    state the statements then assert against; a function would hand back a bag for
    every caller to unpack and re-attach.
    """

    FIXED_CLOCK_NOW = datetime(2026, 7, 14, 12, 0, 0, tzinfo=UTC)

    def __init__(self) -> None:
        self.thrown_exception: Exception | None = None
        self.account_repository = FakeAccountRepository()
        self.password_hasher = FakePasswordHasher()
        self.clock = FakeClock(fixed_now=self.FIXED_CLOCK_NOW)
        self.verification_code_repository = FakeVerificationCodeRepository()
        self.unit_of_work = FakeUnitOfWork()

    def _build_usecase(self) -> RegisterUser:
        return RegisterUser(
            password_hasher=self.password_hasher,
            account_repository=self.account_repository,
            clock=self.clock,
            verification_code_repository=self.verification_code_repository,
            unit_of_work=self.unit_of_work,
        )

    async def _run_register(self, scope: RegisterRequestScope):
        """Execute and capture, never raise. Every caller is a statement whose test
        asserts on the outcome afterwards rather than around the call."""
        try:
            return await self._build_usecase().execute(
                email=scope.email,
                password=scope.password,
                confirm_password=scope.confirm_password,
            )
        except Exception as exc:
            self.thrown_exception = exc
            return None

    def assert_registration_succeeded(self) -> None:
        assert self.thrown_exception is None, (
            f"expected no exception to be raised, got "
            f"{type(self.thrown_exception).__name__}: {self.thrown_exception}"
        )

    def _assert_validation_error_raised(
        self, expected_error_code: str, expected_message: str
    ) -> None:
        assert isinstance(self.thrown_exception, ValidationException), (
            f"expected ValidationException('{expected_error_code}'), got "
            f"{type(self.thrown_exception).__name__ if self.thrown_exception else None}: "
            f"{self.thrown_exception}"
        )
        actual = (self.thrown_exception.error_code, self.thrown_exception.message)
        expected = (expected_error_code, expected_message)
        assert actual == expected, f"expected {expected}, got {actual}"
