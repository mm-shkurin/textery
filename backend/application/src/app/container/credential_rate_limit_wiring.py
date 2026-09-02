"""The per-source bound in front of the three password routes.

Its own module rather than a fourteenth factory in `auth_wiring.py`, which is at
the 200-line cap: this is the only binding there that reads environment
configuration, and the two env constants plus their rationale are what pushed the
file over.
"""

import os

from sqlalchemy.ext.asyncio import AsyncSession

from access.auth.oauth_rate_limit_storage import SqlAlchemyRateLimiter
from auth.rate_limiting import CredentialRateGuard
from container.runtime import request_scoped

RATE_LIMIT_MAX_ENV_VAR = "AUTH_RATE_LIMIT_MAX_REQUESTS"
RATE_LIMIT_WINDOW_ENV_VAR = "AUTH_RATE_LIMIT_WINDOW_SECONDS"
# Per route, per source, per window. Generous next to what one person signing in
# does and far under what one source stuffing credentials needs, so the bound
# costs a shared-NAT office nothing and still ends the attack.
DEFAULT_RATE_LIMIT_MAX_REQUESTS = 20
DEFAULT_RATE_LIMIT_WINDOW_SECONDS = 60

_rate_limit_max = int(os.environ.get(RATE_LIMIT_MAX_ENV_VAR, DEFAULT_RATE_LIMIT_MAX_REQUESTS))
_rate_limit_window = int(
    os.environ.get(RATE_LIMIT_WINDOW_ENV_VAR, DEFAULT_RATE_LIMIT_WINDOW_SECONDS)
)


@request_scoped
def create_credential_rate_guard(session: AsyncSession) -> CredentialRateGuard:
    """The per-source bound in front of `/login`, `/register` and `/resend-code`.

    The SAME store the OAuth legs count in -- one fixed-window table, atomic per
    hit, shared by every replica. An in-process counter would bound one replica
    and leave the deployment's real limit multiplied by however many are running.
    Buckets cannot collide across the two guards: this one keys `login:`,
    `register:` and `resend-code:`, the OAuth guard keys its three leg names.

    The limiter commits its own increment, so the hit counts even when the guarded
    request then fails -- which is every request this bound exists to count.
    """
    return CredentialRateGuard(SqlAlchemyRateLimiter(session, _rate_limit_max, _rate_limit_window))
