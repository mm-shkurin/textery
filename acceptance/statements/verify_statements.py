import uuid

from clients.application.application_client import ApplicationClient
from clients.application.dto.auth.register_request_dto import RegisterRequestDto
from clients.application.dto.auth.verify_request_dto import VerifyRequestDto
from clients.application.dto.auth.verify_response_dto import VerifyResponseDto
from statements.response_assertions import (
    assert_account_verified,
    assert_already_verified_rejected,
)


class VerifyStatements:
    def __init__(self, client: ApplicationClient):
        self._client = client

    async def _register_pending_account_and_build_verify_request(self) -> VerifyRequestDto:
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
        return VerifyRequestDto(email=email, code=code)

    async def given_correct_code_submitted_for_pending_account(self) -> VerifyResponseDto:
        verify_request = await self._register_pending_account_and_build_verify_request()
        return await self._client.verify(verify_request)

    async def given_same_code_submitted_twice_for_pending_account(
        self,
    ) -> tuple[VerifyResponseDto, VerifyResponseDto]:
        verify_request = await self._register_pending_account_and_build_verify_request()
        first = await self._client.verify(verify_request)
        second = await self._client.verify(verify_request)
        return first, second

    async def given_verified_account_then_verify_with_a_different_code(
        self,
    ) -> VerifyResponseDto:
        verify_request = await self._register_pending_account_and_build_verify_request()
        first = await self._client.verify(verify_request)
        assert_account_verified(first)
        last_digit = int(verify_request.code[-1])
        different_code = verify_request.code[:-1] + str((last_digit + 1) % 10)
        assert different_code != verify_request.code, (
            f"setup: derived code {different_code} must differ from {verify_request.code}"
        )
        return await self._client.verify(
            VerifyRequestDto(email=verify_request.email, code=different_code)
        )

    def assert_account_verified(self, response: VerifyResponseDto) -> None:
        assert_account_verified(response)

    def assert_already_verified_rejected(self, response: VerifyResponseDto) -> None:
        assert_already_verified_rejected(response)

    def assert_both_verified(
        self, responses: tuple[VerifyResponseDto, VerifyResponseDto]
    ) -> None:
        first, second = responses
        assert_account_verified(first)
        assert_account_verified(second)
        assert second == first, (
            f"expected re-submitting the same code to be idempotent (second response "
            f"identical to the first), got first={first!r}, second={second!r}"
        )
