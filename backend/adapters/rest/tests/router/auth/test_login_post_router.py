from login_router_fixtures import EXPECTED_TOKEN_PAIR_BODY, given_issued_token_pair

from shared.exceptions import ValidationException


class TestLoginPostRouterValidCredentials:
    """Scenario 6.1: Valid credentials on a verified account issue a token pair.

    Given a verified account and its correct password
    When the client posts them to POST /api/v1/auth/login
    Then the response is 200 carrying the issued pair and both expiries
    And the usecase is awaited once with the submitted email and password
    """

    async def test_should_return_200_with_the_issued_token_pair(self, mocker, login_client):
        mock_usecase = mocker.Mock()
        mock_usecase.execute = mocker.AsyncMock(return_value=given_issued_token_pair())

        async with login_client(mock_usecase) as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": "user@example.com", "password": "Passw0rd1!"},
            )

        assert response.status_code == 200, (
            f"expected 200 OK, got {response.status_code} with body {response.text}"
        )
        assert response.json() == EXPECTED_TOKEN_PAIR_BODY, (
            f"unexpected response body {response.json()}"
        )
        mock_usecase.execute.assert_awaited_once_with(
            email="user@example.com",
            password="Passw0rd1!",
        )


class TestLoginPostRouterInvalidCredentials:
    """Scenario 5.2: Invalid credentials return a single generic error.

    Given the usecase rejects the submitted credentials
    When the client posts them to POST /api/v1/auth/login
    Then the response is 401 with the generic {error_code, message} body
    """

    async def test_should_return_401_with_the_generic_error_body(self, mocker, login_client):
        mock_usecase = mocker.Mock()
        mock_usecase.execute = mocker.AsyncMock(
            side_effect=ValidationException(
                error_code="INVALID_CREDENTIALS",
                message="The email address or password is incorrect.",
            )
        )

        async with login_client(mock_usecase) as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": "user@example.com", "password": "wrong"},
            )

        assert response.status_code == 401, (
            f"expected 401 Unauthorized, got {response.status_code} with body {response.text}"
        )
        assert response.json() == {
            "error_code": "INVALID_CREDENTIALS",
            "message": "The email address or password is incorrect.",
        }, f"unexpected response body {response.json()}"


class TestLoginPostRouterUnverifiedAccount:
    """Scenario 5.1: Login rejected while account is unverified.

    Given the account's password is correct but the account is not yet verified
    When the client posts the credentials to POST /api/v1/auth/login
    Then the response is 403 with the distinct UNVERIFIED code, not the generic 401 —
    the client routes to the verify screen off this code, so it must not collapse
    into INVALID_CREDENTIALS
    """

    async def test_should_return_403_with_the_unverified_error_code(self, mocker, login_client):
        mock_usecase = mocker.Mock()
        mock_usecase.execute = mocker.AsyncMock(
            side_effect=ValidationException(
                error_code="UNVERIFIED",
                message="This account has not been verified yet. Please confirm the code sent to your email.",
            )
        )

        async with login_client(mock_usecase) as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": "pending@example.com", "password": "Passw0rd1!"},
            )

        assert response.status_code == 403, (
            f"expected 403 Forbidden, got {response.status_code} with body {response.text}"
        )
        assert response.json() == {
            "error_code": "UNVERIFIED",
            "message": "This account has not been verified yet. Please confirm the code sent to your email.",
        }, f"unexpected response body {response.json()}"
