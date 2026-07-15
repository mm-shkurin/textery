import uuid

from clients.application.application_client import ApplicationClient
from clients.application.dto.auth.register_request_dto import RegisterRequestDto
from clients.application.dto.auth.verify_request_dto import VerifyRequestDto
from clients.application.dto.auth.verify_response_dto import VerifyResponseDto
from statements.response_assertions import assert_account_verified


class VerifyStatements:
    def __init__(self, client: ApplicationClient):
        self._client = client

    async def given_correct_code_submitted_for_pending_account(self) -> VerifyResponseDto:
        email = f"user-{uuid.uuid4()}@example.com"
        register_request = RegisterRequestDto(
            email=email,
            password="Str0ng!Pass",
            confirm_password="Str0ng!Pass",
        )
        register_response = await self._client.register(register_request)
        code = register_response.body.get("verification_code")
        assert code is not None, (
            f"expected registration to return a verification_code, got body="
            f"{register_response.body}"
        )
        verify_request = VerifyRequestDto(email=email, code=code)
        return await self._client.verify(verify_request)

    def assert_account_verified(self, response: VerifyResponseDto) -> None:
        assert_account_verified(response)
