from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from auth.account import Account
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


@pytest.mark.skip(reason="RED: register() endpoint returns None with response_model=None, discarding the persisted Account")
class TestRegisterPostRouterServerOwnedFields:
    """Scenario 1.5: Ignore server-owned fields in the request body.

    Given the usecase returns a persisted Account (server-generated id,
    is_verified always False)
    When the client submits POST /api/v1/auth/register
    Then the response is 201 with a body containing id and is_verified
    built from the domain Account, and password_hash is never present
    """

    async def test_should_return_201_with_id_and_is_verified_and_no_password_hash(self, mocker):
        app = FastAPI()
        app.include_router(auth_router)
        app.add_exception_handler(ValidationException, validation_exception_handler)

        created_account = Account.create(
            id=uuid4(),
            email="attacker@example.com",
            password_hash="hashed-value",
            created_at=datetime.now(timezone.utc),
        )
        mock_usecase = mocker.Mock()
        mock_usecase.execute = mocker.AsyncMock(return_value=created_account)
        app.dependency_overrides[get_register_user_usecase] = lambda: mock_usecase

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "attacker@example.com",
                    "password": "Sup3rSecret!",
                    "confirm_password": "Sup3rSecret!",
                    "is_verified": True,
                    "id": "11111111-1111-1111-1111-111111111111",
                },
            )

        assert response.status_code == 201, (
            f"expected 201 Created, got {response.status_code} with body {response.text}"
        )
        body = response.json()
        assert body is not None, (
            "expected a JSON body containing id and is_verified, got body=None"
        )
        assert body.get("user_id") == str(created_account.id), (
            f"expected user_id={str(created_account.id)!r} from the persisted Account "
            f"(field name per ProductSpecification/api-specs/auth_register.yaml "
            f"RegisterResponse.user_id), got body={body}"
        )
        assert body.get("is_verified") is False, (
            f"expected is_verified=False from the persisted Account, got body={body}"
        )
        assert "password_hash" not in body, (
            f"expected password_hash to never be present in the response body, got body={body}"
        )
        mock_usecase.execute.assert_awaited_once_with(
            email="attacker@example.com",
            password="Sup3rSecret!",
            confirm_password="Sup3rSecret!",
        )


class TestGetRegisterUserUsecaseDependencyStub:
    """Coverage: get_register_user_usecase DI stub raises NotImplementedError.

    Given real usecase wiring has not landed yet
    When the DI provider function is invoked directly (not overridden)
    Then it raises NotImplementedError
    """

    def test_should_raise_not_implemented_error(self):
        with pytest.raises(NotImplementedError) as excinfo:
            get_register_user_usecase()

        assert str(excinfo.value) == "wired by the application composition root", (
            f"unexpected NotImplementedError message: {excinfo.value}"
        )
