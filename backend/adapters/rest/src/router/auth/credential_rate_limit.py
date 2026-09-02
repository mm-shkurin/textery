"""The per-source abuse bound in front of the three password routes.

Declared here rather than inside the usecases because the subject of the bound is
a transport fact -- who sent the request -- that no usecase otherwise needs. The
guard itself is a usecase-layer object; this module only supplies it the route
name and the caller's identity.
"""

from collections.abc import Awaitable, Callable

from fastapi import Depends, Request

from auth.rate_limiting import CredentialRateGuard
from security.client_source import hashed_client_source

LOGIN_ROUTE = "login"
REGISTER_ROUTE = "register"
RESEND_CODE_ROUTE = "resend-code"


def get_credential_rate_guard() -> CredentialRateGuard:
    """The guard, allow-all until the composition root overrides this.

    It returns a working object instead of raising like the usecase stubs, for
    the reason the analytics stub does: an unwired binding here would turn every
    sign-in into a 500. The wiring is pinned by a test in the application layer
    instead, which is what keeps the fail-open from becoming silent.
    """
    return CredentialRateGuard()


def rate_limited(route: str) -> Callable[..., Awaitable[None]]:
    """The `Depends` guard for one route's bucket.

    A factory rather than one dependency reading the path, because the bucket has
    to be named by the route it guards: sharing one bucket would let a flood of
    registrations lock every caller out of signing in.
    """

    async def enforce(
        request: Request,
        guard: CredentialRateGuard = Depends(get_credential_rate_guard),
    ) -> None:
        await guard.check(route, hashed_client_source(request))

    return enforce
