import pytest
from wiring_support import wired_on_one_session

from access.auth.oauth_rate_limit_storage import SqlAlchemyRateLimiter
from container.auth_wiring import create_credential_rate_guard


@pytest.mark.skip(reason="RED: create_credential_rate_guard is not implemented yet")
class TestCreateCredentialRateGuardWiresTheStore:
    """The guard defaults to allow-all, so an unwired binding throttles nothing.

    The rest layer's provider deliberately returns a working guard rather than
    raising, because a raise there would turn every sign-in into a 500. The price
    of that choice is that a composition root which forgot to override it would
    leave `/login`, `/register` and `/resend-code` unbounded with no symptom at
    all -- every request served, nothing logged. This is the test that makes the
    omission loud.
    """

    async def test_should_wire_the_shared_store_on_the_request_session(self):
        async with wired_on_one_session(create_credential_rate_guard) as (guard, sentinel_session):
            limiter = guard._rate_limiter

            assert isinstance(limiter, SqlAlchemyRateLimiter), (
                "expected the guard to be backed by the cross-instance Postgres "
                f"counter, got {limiter!r} -- an in-process limiter bounds one "
                "replica and the backend runs several"
            )
            assert limiter._session is sentinel_session, (
                "expected the limiter to run on the wiring's own session, got a "
                f"different object {limiter._session!r}"
            )
