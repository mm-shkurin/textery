from statements.oauth_scope import (
    RATE_LIMITED_ERROR,
    configured_rate_limit,
    fake_authorization_code,
    source_headers,
    unique_email,
    unique_subject,
)
from tests.backend.abstract_backend_test import AbstractBackendTest


class TestOAuthRateLimiting(AbstractBackendTest):
    """Security 5.1 — repeated OAuth requests from one source are throttled.

    Each test floods one leg from a single spoofed source (X-Forwarded-For) and
    proves that once the configured per-window rate is exceeded the next request is
    refused with 429, while every request up to the limit is served. A unique source
    per test keeps each flood in its own bucket, so the shared localhost bucket the
    rest of the suite runs on is never spent.
    """

    async def test_5_1_exchange_over_the_rate_is_throttled(self, oauth_statements):
        source = source_headers()
        limit = configured_rate_limit()

        for _ in range(limit):
            served = await oauth_statements.exchange_from(source, "bogus-code")
            assert served.status_code != 429, "a request within the rate was throttled"

        throttled = await oauth_statements.exchange_from(source, "bogus-code")

        assert throttled.status_code == 429, "exchange was not throttled past the rate"
        assert throttled.body["error_code"] == RATE_LIMITED_ERROR

    async def test_5_1_start_over_the_rate_is_throttled(self, oauth_statements):
        source = source_headers()
        limit = configured_rate_limit()

        for _ in range(limit):
            served = await oauth_statements.start_from(source)
            assert served.status_code == 302, "a start within the rate did not redirect"

        throttled = await oauth_statements.start_from(source)

        assert throttled.status_code == 429, "start was not throttled past the rate"

    async def test_5_1_callback_over_the_rate_is_throttled(self, oauth_statements):
        source = source_headers()
        limit = configured_rate_limit()
        code = fake_authorization_code(unique_subject(), unique_email())

        for _ in range(limit):
            served = await oauth_statements.callback_from(source, code=code, state="x")
            assert served.status_code == 302, "a callback within the rate did not redirect"

        throttled = await oauth_statements.callback_from(source, code=code, state="x")

        assert throttled.status_code == 429, "callback was not throttled past the rate"
