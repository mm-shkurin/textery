"""The abuse bound the password routes share.

Separate from `auth.oauth.rate_limiter`, which owns the same shape for the three
OAuth legs, because the two answer different error codes and the OAuth guard's
buckets are keyed by leg. The *port* and its allow-all default live here and are
imported there, so one store implementation serves both.
"""

from datetime import datetime
from typing import Protocol

from shared.clock import Clock, SystemClock
from shared.error_codes import ErrorCode
from shared.exceptions import ValidationException


class RateLimiter(Protocol):
    """A shared, cross-instance abuse bound.

    The count lives in a store all instances read, so a caller cannot dodge the
    limit by landing on a different backend. Each hit is registered atomically --
    the return says whether this hit is still inside the window's allowance.
    """

    async def register_hit(self, bucket_key: str, now: datetime) -> bool:
        """Record one hit against the current window; True if within the limit."""
        ...


class AllowAllRateLimiter:
    """The default when no store is wired (unit tests, in-process harness).

    Never throttles. The real bound is a deployment concern supplied by the
    composition root; a caller constructed without one must still run.
    """

    async def register_hit(self, bucket_key: str, now: datetime) -> bool:
        return True


class CredentialRateGuard:
    """The per-source bound in front of `/login`, `/register` and `/resend-code`.

    The per-account lockout already bounds guessing at ONE account. It does
    nothing about one source spreading its attempts across many accounts, which
    is what credential stuffing is: every individual account stays under its own
    threshold while the source runs unbounded. This guard is keyed on the source
    instead, so the total from one origin is what gets capped.

    Buckets are per (route, source): a flood of `/register` from one caller never
    spends that caller's `/login` allowance, and never spends another caller's.
    """

    MESSAGE = "Too many attempts from this source. Please try again later."

    def __init__(self, rate_limiter: RateLimiter | None = None, clock: Clock | None = None) -> None:
        self._rate_limiter = rate_limiter or AllowAllRateLimiter()
        self._clock = clock or SystemClock()

    async def check(self, route: str, source: str) -> None:
        """Register this attempt against the (route, source) bucket, or refuse it.

        The hit is registered even when the guarded operation goes on to fail --
        a refused password still spends allowance, which is the only reason a
        bound on failed attempts bounds anything.
        """
        if not await self._rate_limiter.register_hit(f"{route}:{source}", self._clock.now()):
            raise ValidationException(self.MESSAGE, ErrorCode.AUTH_RATE_LIMITED)
