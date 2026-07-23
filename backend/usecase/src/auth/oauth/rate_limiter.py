from datetime import datetime
from typing import Protocol

from auth.oauth.oauth_error_codes import OAUTH_RATE_LIMITED
from shared.exceptions import ValidationException


class RateLimiter(Protocol):
    """A shared, cross-instance abuse bound for the OAuth legs.

    The count lives in a store all instances read, so a caller cannot dodge the
    limit by landing on a different backend. Each hit is registered atomically —
    the return says whether this hit is still inside the window's allowance.
    """

    async def register_hit(self, bucket_key: str, now: datetime) -> bool:
        """Record one hit against the current window; True if within the limit."""
        ...


class AllowAllRateLimiter:
    """The default when no store is wired (unit tests, in-process harness).

    Never throttles. The real bound is a deployment concern supplied by the
    composition root; a usecase constructed without one must still run.
    """

    async def register_hit(self, bucket_key: str, now: datetime) -> bool:
        return True


class OAuthRateGuard:
    """Shared abuse-bound check the three OAuth usecases delegate to.

    Extracted here rather than duplicated per usecase, and deliberately not a
    usecase itself: it orchestrates no user-visible operation, it is a helper the
    top-level legs call. Buckets are per (leg, source) so a flood of one leg from
    one caller never spends another leg's or another caller's allowance.
    """

    def __init__(self, rate_limiter: RateLimiter | None = None) -> None:
        self._rate_limiter = rate_limiter or AllowAllRateLimiter()

    async def check(self, leg: str, source: str, now: datetime) -> None:
        if not await self._rate_limiter.register_hit(f"{leg}:{source}", now):
            raise ValidationException(
                "too many OAuth requests from this source", OAUTH_RATE_LIMITED
            )
