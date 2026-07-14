from typing import ClassVar

from clients.application.application_client import ApplicationClient
from clients.application.dto.auth.register_response_dto import RegisterResponseDto
from statements.auth_scope import RegisterScope
from statements.response_assertions import assert_validation_error

MALFORMED_EMAIL = "not-an-email"
OVERLONG_EMAIL_LOCAL_PART_LENGTH = 244


class AuthStatements:
    # Errors use the uniform { error_code, message } shape per
    # ProductSpecification/stories/07-authorization/endpoints.md.
    EXPECTED_MALFORMED_EMAIL_ERROR: ClassVar[dict] = {
        "error_code": "INVALID_EMAIL",
        "message": "The email address is not valid.",
    }
    EXPECTED_OVERLONG_EMAIL_ERROR: ClassVar[dict] = EXPECTED_MALFORMED_EMAIL_ERROR

    def __init__(self, client: ApplicationClient):
        self._client = client

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
