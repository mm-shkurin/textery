import asyncio
import uuid

from clients.application.application_client import ApplicationClient
from clients.application.dto.auth.register_response_dto import RegisterResponseDto
from clients.application.dto.auth.verify_request_dto import VerifyRequestDto
from statements.auth_scope import RegisterScope


async def given_duplicate_registration_against_pending_account(
    client: ApplicationClient,
) -> RegisterResponseDto:
    email = f"pending-dup-{uuid.uuid4()}@example.com"
    await _register_with_email(client, email)
    return await _register_with_email(client, email)


async def given_duplicate_registration_against_verified_account(
    client: ApplicationClient,
) -> RegisterResponseDto:
    email = f"verified-dup-{uuid.uuid4()}@example.com"
    first_response = await _register_with_email(client, email)
    code = first_response.body.get("verification_code") if first_response.body else None
    await client.verify(VerifyRequestDto(email=email, code=code))
    return await _register_with_email(client, email)


async def given_identical_registration_request_retried(
    client: ApplicationClient,
) -> RegisterResponseDto:
    email = f"retry-{uuid.uuid4()}@example.com"
    scope = RegisterScope.builder(email=email)
    request = scope.to_request_dto()
    await client.register(request)
    return await client.register(request)


async def given_duplicate_registration_with_different_case(
    client: ApplicationClient,
) -> RegisterResponseDto:
    local_part = uuid.uuid4().hex
    original_email = f"user-{local_part}@example.ru"
    cased_email = f"USER-{local_part}@Example.ru"
    await _register_with_email(client, original_email)
    return await _register_with_email(client, cased_email)


async def given_two_concurrent_registrations_for_same_new_email(
    client: ApplicationClient,
) -> tuple[RegisterResponseDto, RegisterResponseDto]:
    email = f"concurrent-{uuid.uuid4()}@example.com"
    scope = RegisterScope.builder(email=email)
    request = scope.to_request_dto()
    first_response, second_response = await asyncio.gather(
        client.register(request), client.register(request)
    )
    return first_response, second_response


def assert_exactly_one_account_created(
    responses: tuple[RegisterResponseDto, RegisterResponseDto],
    expected_duplicate_error: dict,
) -> None:
    created = [response for response in responses if response.status_code == 201]
    rejected = [response for response in responses if response.status_code == 409]
    assert len(created) == 1, (
        f"expected exactly one 201 Created among concurrent responses, "
        f"got status_codes={[r.status_code for r in responses]}"
    )
    assert len(rejected) == 1, (
        f"expected exactly one 409 Conflict among concurrent responses, "
        f"got status_codes={[r.status_code for r in responses]}"
    )
    assert rejected[0].body == expected_duplicate_error, (
        f"expected the rejected response body {expected_duplicate_error}, "
        f"got {rejected[0].body}"
    )


async def _register_with_email(client: ApplicationClient, email: str) -> RegisterResponseDto:
    scope = RegisterScope.builder(email=email)
    request = scope.to_request_dto()
    return await client.register(request)
