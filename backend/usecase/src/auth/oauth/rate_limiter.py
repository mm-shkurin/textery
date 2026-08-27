from datetime import datetime

from auth.oauth.oauth_error_codes import OAUTH_RATE_LIMITED
from auth.rate_limiting import AllowAllRateLimiter, RateLimiter
from shared.exceptions import ValidationException

__all__ = ["AllowAllRateLimiter", "OAuthRateGuard", "RateLimiter"]


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
