from datetime import UTC, datetime

from auth.rate_limiting import CredentialRateGuard
from fake.auth.fake_clock import FakeClock
from fake.auth.fake_rate_limiter import FakeRateLimiter
from shared.exceptions import ValidationException


class CredentialRateGuardStatements:
    """The per-source bound in front of the three password routes."""

    FIXED_CLOCK_NOW = datetime(2026, 8, 27, 12, 0, 0, tzinfo=UTC)
    MAX_REQUESTS = 3
    WINDOW_SECONDS = 60
    LOGIN_ROUTE = "login"
    REGISTER_ROUTE = "register"
    ONE_SOURCE = "d1f4a0be9c3b4e2f8a7c6d5e4f3a2b10"
    ANOTHER_SOURCE = "0b2a3f4e5d6c7b8a9f2e3d4c5b6a7f81"
    # Spelled out rather than imported from the guard: importing the constant the
    # assertion pins would make it pass for any edit to it.
    MESSAGE = "Too many attempts from this source. Please try again later."
    ERROR_CODE = "AUTH_RATE_LIMITED"

    def __init__(self) -> None:
        self._rate_limiter = FakeRateLimiter(self.MAX_REQUESTS, self.WINDOW_SECONDS)
        self._guard = CredentialRateGuard(
            rate_limiter=self._rate_limiter,
            clock=FakeClock(fixed_now=self.FIXED_CLOCK_NOW),
        )
        self.thrown_exception: Exception | None = None

    async def given_the_allowance_spent_by_one_source(self) -> None:
        for _ in range(self.MAX_REQUESTS):
            await self._guard.check(self.LOGIN_ROUTE, self.ONE_SOURCE)

    async def attempt_once_more(self) -> None:
        await self._attempt(self.LOGIN_ROUTE, self.ONE_SOURCE)

    async def attempt_from_another_source(self) -> None:
        await self._attempt(self.LOGIN_ROUTE, self.ANOTHER_SOURCE)

    async def attempt_on_another_route(self) -> None:
        await self._attempt(self.REGISTER_ROUTE, self.ONE_SOURCE)

    async def _attempt(self, route: str, source: str) -> None:
        self.thrown_exception = None
        try:
            await self._guard.check(route, source)
        except Exception as exception:
            self.thrown_exception = exception

    def assert_refused_as_rate_limited(self) -> None:
        exception = self.thrown_exception
        assert isinstance(exception, ValidationException), (
            f"expected a ValidationException refusing the attempt, got {exception!r}"
        )
        assert exception.error_code == self.ERROR_CODE, (
            f"expected the {self.ERROR_CODE} code so the route answers 429, "
            f"got {exception.error_code!r}"
        )
        assert exception.message == self.MESSAGE, (
            f"expected the fixed client-safe message, got {exception.message!r}"
        )

    def assert_allowed(self) -> None:
        assert self.thrown_exception is None, (
            f"expected the attempt to be allowed, it was refused with {self.thrown_exception!r}"
        )
