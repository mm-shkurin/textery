import uuid
from datetime import datetime, timezone
from typing import ClassVar

from clients.application.application_client import ApplicationClient
from clients.application.dto.auth.register_response_dto import RegisterResponseDto
from statements.auth_scope import RegisterScope
from statements.response_assertions import assert_is_valid_uuid, assert_validation_error
from statements.verification_code_assertions import (
    assert_code_expiry_within_window,
    assert_valid_verification_code,
)

MALFORMED_EMAIL = "not-an-email"
OVERLONG_EMAIL_LOCAL_PART_LENGTH = 244
SECRET_RESPONSE_FIELDS = ("password", "confirm_password", "password_hash")


class AuthStatements:
    # Errors use the uniform { error_code, message } shape per
    # ProductSpecification/stories/07-authorization/endpoints.md.
    EXPECTED_MALFORMED_EMAIL_ERROR: ClassVar[dict] = {
        "error_code": "INVALID_EMAIL",
        "message": "The email address is not valid.",
    }
    EXPECTED_OVERLONG_EMAIL_ERROR: ClassVar[dict] = EXPECTED_MALFORMED_EMAIL_ERROR
    EXPECTED_WEAK_PASSWORD_ERROR: ClassVar[dict] = {
        "error_code": "INVALID_PASSWORD",
        "message": "The password does not meet the password policy.",
    }
    EXPECTED_PASSWORD_MISMATCH_ERROR: ClassVar[dict] = {
        "error_code": "PASSWORD_MISMATCH",
        "message": "The password confirmation does not match.",
    }
    ATTACKER_SUPPLIED_ID: ClassVar[str] = "11111111-1111-1111-1111-111111111111"

    def __init__(self, client: ApplicationClient):
        self._client = client
        self._last_request_window: tuple[datetime, datetime] | None = None

    async def given_registration_request_with_malformed_email(self) -> RegisterResponseDto:
        scope = RegisterScope.builder(email=MALFORMED_EMAIL)
        request = scope.to_request_dto()
        return await self._client.register(request)

    async def given_registration_request_with_overlong_email(self) -> RegisterResponseDto:
        local_part = "a" * OVERLONG_EMAIL_LOCAL_PART_LENGTH
        overlong_email = f"{local_part}@example.com"
        assert len(overlong_email) == 256, (
            f"expected a 256-character email fixture, got {len(overlong_email)} chars"
        )
        scope = RegisterScope.builder(email=overlong_email)
        request = scope.to_request_dto()
        return await self._client.register(request)

    async def given_registration_request_with_short_password(self) -> RegisterResponseDto:
        return await self._register_with_password("Ab1!abc")

    async def given_registration_request_with_password_missing_digit(self) -> RegisterResponseDto:
        return await self._register_with_password("Abcdefgh!")

    async def given_registration_request_with_password_missing_uppercase(self) -> RegisterResponseDto:
        return await self._register_with_password("abcdefg1!")

    async def given_registration_request_with_password_missing_lowercase(self) -> RegisterResponseDto:
        return await self._register_with_password("ABCDEFG1!")

    async def given_registration_request_with_password_missing_special_character(
        self,
    ) -> RegisterResponseDto:
        return await self._register_with_password("Abcdefg1")

    async def given_registration_request_with_overlong_password(self) -> RegisterResponseDto:
        password = "A1!" + "a" * 126
        assert len(password) == 129, (
            f"expected a 129-character password fixture, got {len(password)} chars"
        )
        return await self._register_with_password(password)

    async def given_registration_request_with_mismatched_confirm_password(
        self,
    ) -> RegisterResponseDto:
        scope = RegisterScope.builder(password="Str0ng!Pass", confirm_password="Different!9")
        request = scope.to_request_dto()
        return await self._client.register(request)

    async def given_registration_request_with_server_owned_fields(
        self,
    ) -> RegisterResponseDto:
        scope = RegisterScope.builder(
            email="attacker@example.com",
            extra_fields={"is_verified": True, "id": self.ATTACKER_SUPPLIED_ID},
        )
        request = scope.to_request_dto()
        return await self._client.register(request)

    async def given_valid_unique_registration_request(self) -> RegisterResponseDto:
        unique_email = f"user-{uuid.uuid4()}@example.com"
        scope = RegisterScope.builder(email=unique_email)
        request = scope.to_request_dto()
        # Bracket the call so the expiry assertion can check code_expires_at
        # against [sent_at + TTL, received_at + TTL] instead of a single
        # post-response "now" padded with a wide fixed tolerance - that would
        # hide a wrong TTL behind request latency.
        sent_at = datetime.now(timezone.utc)
        response = await self._client.register(request)
        received_at = datetime.now(timezone.utc)
        self._last_request_window = (sent_at, received_at)
        return response

    async def _register_with_password(self, password: str) -> RegisterResponseDto:
        scope = RegisterScope.builder(password=password, confirm_password=password)
        request = scope.to_request_dto()
        return await self._client.register(request)

    def assert_validation_error(self, response: RegisterResponseDto, expected_error: dict) -> None:
        assert_validation_error(response, expected_error)

    def assert_no_account_created(self, response: RegisterResponseDto) -> None:
        assert response.status_code not in (200, 201), (
            f"expected no account to be created (2xx would indicate creation), "
            f"got status_code={response.status_code}"
        )
        assert response.body is not None, (
            "expected an error body proving no account was created, got body=None"
        )
        assert "user_id" not in response.body, (
            f"expected no user_id in response, but got body={response.body}"
        )

    def _assert_created_pending_account(self, response: RegisterResponseDto) -> dict:
        assert response.status_code == 201, (
            f"expected 201 Created, got status_code={response.status_code}, body={response.body}"
        )
        assert response.body is not None, (
            "expected a response body for the created account, got body=None"
        )
        is_verified = response.body.get("is_verified")
        assert is_verified is False, (
            f"expected newly created account is_verified=False, got is_verified={is_verified!r}"
        )
        leaked = [field for field in SECRET_RESPONSE_FIELDS if field in response.body]
        assert not leaked, (
            f"expected none of {SECRET_RESPONSE_FIELDS} in the response body, "
            f"found {leaked} (body={response.body})"
        )
        return response.body

    def assert_server_owned_fields_ignored(self, response: RegisterResponseDto) -> None:
        body = self._assert_created_pending_account(response)
        # user_id is category 4 (truly opaque) per the determinism hierarchy: it is a
        # server-generated UUID with no setup-capturable exact value, so we assert
        # it is present and well-formed (not just "not equal to the attacker's id" —
        # that alone would pass on user_id=None, which is the exact defect this test
        # guards against) plus the scenario-specific inequality. Field name per
        # ProductSpecification/api-specs/auth_register.yaml's RegisterResponse schema.
        account_id = body.get("user_id")
        assert account_id is not None, (
            f"expected a server-generated user_id, got user_id=None (body={body})"
        )
        assert_is_valid_uuid(account_id, field_name="user_id")
        assert account_id != self.ATTACKER_SUPPLIED_ID, (
            f"expected a server-generated user_id, not the attacker-supplied id "
            f"{self.ATTACKER_SUPPLIED_ID!r}, got user_id={account_id!r}"
        )

    def assert_pending_account_created_with_verification_code(
        self, response: RegisterResponseDto
    ) -> None:
        body = self._assert_created_pending_account(response)
        assert_valid_verification_code(body.get("verification_code"))
        assert self._last_request_window is not None, (
            "assert_pending_account_created_with_verification_code requires the response "
            "from given_valid_unique_registration_request, which records the request window"
        )
        sent_at, received_at = self._last_request_window
        assert_code_expiry_within_window(body.get("code_expires_at"), sent_at, received_at)
