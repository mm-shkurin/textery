import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from shared.exceptions import ValidationException
from error_handling.exception_handlers import validation_exception_handler

auth_router_module = pytest.importorskip(
    "router.auth.auth_router",
    reason="RED: router.auth.auth_router module does not exist (ModuleNotFoundError)",
)
auth_router = auth_router_module.router
get_register_user_usecase = auth_router_module.get_register_user_usecase


class TestRegisterPostRouterMalformedEmail:
    """Scenario 1.1: Reject malformed email.

    Given a registration request with a malformed email address
    When the client submits POST /api/v1/auth/register
    Then the response is 400 with {error_code, message} body
    """

    async def test_should_return_400_with_error_code_and_message_for_malformed_email(self, mocker):
        app = FastAPI()
        app.include_router(auth_router)
        app.add_exception_handler(ValidationException, validation_exception_handler)

        mock_usecase = mocker.Mock()
        mock_usecase.execute = mocker.AsyncMock(
            side_effect=ValidationException(
                error_code="INVALID_EMAIL",
                message="The email address is not valid.",
            )
        )
        app.dependency_overrides[get_register_user_usecase] = lambda: mock_usecase

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "not-an-email",
                    "password": "Sup3rSecret!",
                    "confirm_password": "Sup3rSecret!",
                },
            )

        assert response.status_code == 400, (
            f"expected 400 Bad Request, got {response.status_code} with body {response.text}"
        )
        assert response.json() == {
            "error_code": "INVALID_EMAIL",
            "message": "The email address is not valid.",
        }, f"unexpected response body {response.json()}"
        mock_usecase.execute.assert_awaited_once_with(
            email="not-an-email",
            password="Sup3rSecret!",
            confirm_password="Sup3rSecret!",
        )
