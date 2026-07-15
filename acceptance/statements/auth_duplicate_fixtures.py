import uuid

from clients.application.application_client import ApplicationClient
from clients.application.dto.auth.register_response_dto import RegisterResponseDto
from clients.application.dto.auth.verify_request_dto import VerifyRequestDto
from statements.auth_scope import RegisterScope


async def register_with_email(client: ApplicationClient, email: str) -> RegisterResponseDto:
    scope = RegisterScope.builder(email=email)
    request = scope.to_request_dto()
    return await client.register(request)


async def duplicate_registration_against_pending_account(
    client: ApplicationClient,
) -> RegisterResponseDto:
    email = f"pending-dup-{uuid.uuid4()}@example.com"
    await register_with_email(client, email)
    return await register_with_email(client, email)


async def duplicate_registration_against_verified_account(
    client: ApplicationClient,
) -> RegisterResponseDto:
    email = f"verified-dup-{uuid.uuid4()}@example.com"
    first_response = await register_with_email(client, email)
    code = first_response.body.get("verification_code") if first_response.body else None
    await client.verify(VerifyRequestDto(email=email, code=code))
    return await register_with_email(client, email)
