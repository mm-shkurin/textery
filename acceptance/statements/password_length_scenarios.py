import uuid

from clients.application.application_client import ApplicationClient
from clients.application.dto.auth.register_response_dto import RegisterResponseDto
from statements.auth_scope import RegisterScope

MULTIBYTE_PASSWORD_CODE_POINT_COUNT = 128
_MULTIBYTE_FILLER_CHAR = "é"


def _build_multibyte_password(code_point_count: int) -> str:
    prefix = "Aa1!"
    filler = _MULTIBYTE_FILLER_CHAR * (code_point_count - len(prefix))
    return prefix + filler


async def given_registration_request_with_multibyte_password_at_length_limit(
    client: ApplicationClient,
) -> RegisterResponseDto:
    password = _build_multibyte_password(MULTIBYTE_PASSWORD_CODE_POINT_COUNT)
    assert len(password) == 128, (
        f"expected a 128-code-point password fixture, got {len(password)} code points"
    )
    assert len(password.encode("utf-8")) > 128, (
        "expected the fixture to be multibyte (more UTF-8 bytes than code points)"
    )
    # This scenario accepts the request and creates an account, so the email
    # must be unique per invocation - unlike the rejected-password variants
    # in auth_statements.py, which never reach account creation and can
    # safely reuse a fixed email across repeated test runs.
    email = f"multibyte-pw-{uuid.uuid4()}@example.com"
    return await _register_with_credentials(client, email, password)


async def given_registration_request_with_multibyte_password_over_length_limit(
    client: ApplicationClient,
) -> RegisterResponseDto:
    password = _build_multibyte_password(MULTIBYTE_PASSWORD_CODE_POINT_COUNT + 1)
    assert len(password) == 129, (
        f"expected a 129-code-point password fixture, got {len(password)} code points"
    )
    return await _register_with_password(client, password)


async def _register_with_password(
    client: ApplicationClient, password: str
) -> RegisterResponseDto:
    scope = RegisterScope.builder(password=password, confirm_password=password)
    request = scope.to_request_dto()
    return await client.register(request)


async def _register_with_credentials(
    client: ApplicationClient, email: str, password: str
) -> RegisterResponseDto:
    scope = RegisterScope.builder(email=email, password=password, confirm_password=password)
    request = scope.to_request_dto()
    return await client.register(request)
