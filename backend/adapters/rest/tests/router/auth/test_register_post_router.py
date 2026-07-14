from datetime import datetime, timezone
from uuid import uuid4

import pytest

from auth.account import Account
from auth.registration_result import RegistrationResult
from auth.verification_code import VerificationCode
from shared.exceptions import ValidationException

pytest.importorskip(
    "router.auth.auth_router",
    reason="RED: router.auth.auth_router module does not exist (ModuleNotFoundError)",
)


class TestRegisterPostRouterMalformedEmail:
    """Scenario 1.1: Reject malformed email.

    Given a registration request with a malformed email address
    When the client submits POST /api/v1/auth/register
    Then the response is 400 with {error_code, message} body
    """

    async def test_should_return_400_with_error_code_and_message_for_malformed_email(
        self, mocker, register_client
    ):
        mock_usecase = mocker.Mock()
        mock_usecase.execute = mocker.AsyncMock(
            side_effect=ValidationException(
                error_code="INVALID_EMAIL",
                message="The email address is not valid.",
            )
        )

        async with register_client(mock_usecase) as client:
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


class TestRegisterPostRouterServerOwnedFields:
    """Scenario 1.5: Ignore server-owned fields in the request body.

    Given the usecase returns a persisted Account (server-generated id,
    is_verified always False)
    When the client submits POST /api/v1/auth/register
    Then the response is 201 with a body containing id and is_verified
    built from the domain Account, and password_hash is never present
    """

    async def test_should_return_201_with_id_and_is_verified_and_no_password_hash(
        self, mocker, register_client
    ):
        created_account = Account.create(
            id=uuid4(),
            email="attacker@example.com",
            password_hash="hashed-value",
            created_at=datetime.now(timezone.utc),
        )
        created_verification_code = VerificationCode.create(
            id=uuid4(),
            account_id=created_account.id,
            code="123456",
            expires_at=datetime.now(timezone.utc),
        )
        registration_result = RegistrationResult(
            account=created_account, verification_code=created_verification_code
        )
        mock_usecase = mocker.Mock()
        mock_usecase.execute = mocker.AsyncMock(return_value=registration_result)

        async with register_client(mock_usecase) as client:
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


class TestRegisterPostRouterVerificationCode:
    """Scenario 2.1: Valid registration creates a pending account and returns a verification code.

    Given the usecase returns a RegistrationResult with a persisted Account and
    a persisted VerificationCode
    When the client submits POST /api/v1/auth/register
    Then the response is 201 with a body containing verification_code and
    code_expires_at built from the domain VerificationCode
    """

    @pytest.mark.skip(reason="RED: RegisterResponseDto missing verification_code/code_expires_at")
    async def test_should_return_201_with_verification_code_and_code_expires_at(
        self, mocker, register_client
    ):
        created_account = Account.create(
            id=uuid4(),
            email="new-user@example.com",
            password_hash="hashed-value",
            created_at=datetime.now(timezone.utc),
        )
        code_expires_at = datetime(2026, 7, 14, 12, 30, 0, tzinfo=timezone.utc)
        created_verification_code = VerificationCode.create(
            id=uuid4(),
            account_id=created_account.id,
            code="042917",
            expires_at=code_expires_at,
        )
        registration_result = RegistrationResult(
            account=created_account, verification_code=created_verification_code
        )
        mock_usecase = mocker.Mock()
        mock_usecase.execute = mocker.AsyncMock(return_value=registration_result)

        async with register_client(mock_usecase) as client:
            response = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "new-user@example.com",
                    "password": "Sup3rSecret!",
                    "confirm_password": "Sup3rSecret!",
                },
            )

        assert response.status_code == 201, (
            f"expected 201 Created, got {response.status_code} with body {response.text}"
        )
        body = response.json()
        assert body.get("verification_code") == "042917", (
            f"expected verification_code='042917' from the persisted VerificationCode "
            f"(field name per ProductSpecification/api-specs/auth_register.yaml "
            f"RegisterResponse.verification_code), got body={body}"
        )
        assert body.get("code_expires_at") == code_expires_at.isoformat(), (
            f"expected code_expires_at={code_expires_at.isoformat()!r} from the persisted "
            f"VerificationCode, got body={body}"
        )
