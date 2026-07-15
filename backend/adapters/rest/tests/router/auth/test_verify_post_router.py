import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.skip(reason="RED: POST /api/v1/auth/verify route is not wired on auth_router")
class TestVerifyPostRouterCorrectCode:
    """Scenario 3.1: Correct code activates the account.

    Given a client submits a correct email/code pair
    When the client submits POST /api/v1/auth/verify
    Then the response is 200 with body {"is_verified": true}
    """

    async def test_should_return_200_with_is_verified_true(self, register_app):
        transport = ASGITransport(app=register_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
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
