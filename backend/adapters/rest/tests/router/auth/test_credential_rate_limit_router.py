import pytest
from credential_rate_limit_fixtures import MAX_REQUESTS, RATE_LIMITED_BODY, credentials_for
from login_router_fixtures import given_issued_token_pair


@pytest.mark.skip(reason="RED: the password routes do not declare a rate-limit guard yet")
class TestCredentialRateLimitAcrossAccounts:
    """One source, many accounts: the shape the per-account lockout cannot see.

    Given a source that has spent its allowance on POST /api/v1/auth/login,
    each attempt against a DIFFERENT account so no account's own failure counter
    ever reaches its threshold
    When the same source posts once more
    Then the response is 429 with the AUTH_RATE_LIMITED code
    And the usecase is never reached for that attempt
    """

    async def test_should_return_429_on_the_attempt_after_the_allowance(
        self, mocker, rate_limited_login_client
    ):
        mock_usecase = mocker.Mock()
        mock_usecase.execute = mocker.AsyncMock(return_value=given_issued_token_pair())

        async with rate_limited_login_client(mock_usecase) as client:
            for attempt in range(MAX_REQUESTS):
                allowed = await client.post("/api/v1/auth/login", json=credentials_for(attempt))
                assert allowed.status_code == 200, (
                    f"attempt {attempt} was inside the allowance and should have been "
                    f"served, got {allowed.status_code} with body {allowed.text}"
                )
            response = await client.post("/api/v1/auth/login", json=credentials_for(MAX_REQUESTS))

        assert response.status_code == 429, (
            f"expected 429 Too Many Requests once the source spent its allowance, got "
            f"{response.status_code} with body {response.text}"
        )
        assert response.json() == RATE_LIMITED_BODY, f"unexpected response body {response.json()}"
        assert mock_usecase.execute.await_count == MAX_REQUESTS, (
            "expected the refused attempt to be turned away before the usecase, so "
            f"only the allowed attempts reached it, got {mock_usecase.execute.await_count}"
        )
