import uuid
from dataclasses import dataclass

from clients.application.application_client import ApplicationClient
from clients.application.dto.auth.login_request_dto import LoginRequestDto
from clients.application.dto.auth.register_request_dto import RegisterRequestDto
from clients.application.dto.auth.verify_request_dto import VerifyRequestDto
from statements.response_assertions import assert_account_verified, assert_created_pending_account

ACCOUNT_PASSWORD = "Str0ng!Pass"
JWT_SEGMENTS = 3


@dataclass(frozen=True)
class AuthenticatedAccount:
    email: str
    access_token: str


async def register_verify_and_login(client: ApplicationClient) -> AuthenticatedAccount:
    """Provision one verified account and return its access token.

    Setup runs through the public auth endpoints only — an acceptance test never
    reaches into storage, so "an authenticated user" means the same three calls a
    real client makes. Each step is checked with the shared response assertions rather
    than a local status compare, so a change to the auth contract fails here too.
    """
    email = f"acceptance-{uuid.uuid4()}@example.com"
    register_response = await client.register(
        RegisterRequestDto(
            email=email, password=ACCOUNT_PASSWORD, confirm_password=ACCOUNT_PASSWORD
        )
    )
    register_body = assert_created_pending_account(register_response)
    code = register_body.get("verification_code")
    assert code is not None, (
        f"setup: expected registration to issue a verification_code, got body={register_body}"
    )

    assert_account_verified(await client.verify(VerifyRequestDto(email=email, code=code)))

    login_response = await client.login(
        LoginRequestDto(email=email, password=ACCOUNT_PASSWORD)
    )
    assert login_response.status_code == 200, (
        f"setup: expected 200 logging in {email}, got "
        f"status_code={login_response.status_code}, body={login_response.body}"
    )
    access_token = (login_response.body or {}).get("access_token")
    return AuthenticatedAccount(email=email, access_token=_asserted_jwt(access_token))


def _asserted_jwt(access_token: object) -> str:
    """A three-segment, non-empty JWT — not merely "not None".

    A blank or truncated token would make every guarded probe answer 401, and the
    scenario would read as a passing 404 guard while never reaching the guard at all.
    """
    assert isinstance(access_token, str), (
        f"setup: expected login to issue a string access_token, got {access_token!r}"
    )
    segments = access_token.split(".")
    assert len(segments) == JWT_SEGMENTS and all(segments), (
        f"setup: expected a {JWT_SEGMENTS}-segment JWT access token, "
        f"got {len(segments)} non-empty segments"
    )
    return access_token
