class TestVerifyPostRouterCorrectCode:
    """Scenario 3.1: Correct code activates the account.

    Given a pending account with an active, unexpired verification code
    When the client submits that code for that email via POST /api/v1/auth/verify
    Then the response is 200 with body {"is_verified": true}
    And the usecase is awaited once with the submitted email and code
    """

    async def test_should_return_200_with_is_verified_true(self, mocker, verify_client):
        mock_usecase = mocker.Mock()
        mock_usecase.execute = mocker.AsyncMock(return_value=None)

        async with verify_client(mock_usecase) as client:
            response = await client.post(
                "/api/v1/auth/verify",
                json={
                    "email": "new-user@example.com",
                    "code": "042917",
                },
            )

        assert response.status_code == 200, (
            f"expected 200 OK, got {response.status_code} with body {response.text}"
        )
        assert response.json() == {"is_verified": True}, (
            f"unexpected response body {response.json()}"
        )
        mock_usecase.execute.assert_awaited_once_with(
            email="new-user@example.com",
            code="042917",
        )
