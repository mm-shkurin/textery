from login_router_fixtures import EXPECTED_TOKEN_PAIR_BODY, given_issued_token_pair

from shared.exceptions import ValidationException


class TestRefreshPostRouterValidToken:
    """Scenario 6.2: Refresh returns a new access token for a valid refresh token.

    Given a valid, unexpired refresh token
    When the client posts it to POST /api/v1/auth/refresh
    Then the response is 200 carrying the fresh pair and both expiries
    And the usecase is awaited once with the submitted refresh token
    """

    async def test_should_return_200_with_the_issued_token_pair(self, mocker, refresh_client):
        mock_usecase = mocker.Mock()
        mock_usecase.execute = mocker.AsyncMock(return_value=given_issued_token_pair())

        async with refresh_client(mock_usecase) as client:
            response = await client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": "a.valid.refresh"},
            )

        assert response.status_code == 200, (
            f"expected 200 OK, got {response.status_code} with body {response.text}"
        )
        assert response.json() == EXPECTED_TOKEN_PAIR_BODY, (
            f"unexpected response body {response.json()}"
        )
        mock_usecase.execute.assert_awaited_once_with(refresh_token="a.valid.refresh")


class TestRefreshPostRouterInvalidToken:
    """Scenario 6.3: Refresh rejects an expired or invalid refresh token.

    Given the usecase rejects the submitted refresh token
    When the client posts it to POST /api/v1/auth/refresh
    Then the response is 401 with the generic {error_code, message} body
    """

    async def test_should_return_401_with_the_generic_error_body(self, mocker, refresh_client):
        mock_usecase = mocker.Mock()
        mock_usecase.execute = mocker.AsyncMock(
            side_effect=ValidationException(
                error_code="INVALID_REFRESH_TOKEN",
                message="The refresh token is invalid or has expired.",
            )
        )

        async with refresh_client(mock_usecase) as client:
            response = await client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": "expired.or.forged"},
            )

        assert response.status_code == 401, (
            f"expected 401 Unauthorized, got {response.status_code} with body {response.text}"
        )
        assert response.json() == {
            "error_code": "INVALID_REFRESH_TOKEN",
            "message": "The refresh token is invalid or has expired.",
        }, f"unexpected response body {response.json()}"
