import asyncio
import base64
import json
import uuid

from clients.application.application_client import ApplicationClient
from clients.application.dto.auth.login_request_dto import LoginRequestDto
from clients.application.dto.auth.oauth_dtos import OAuthExchangeResponseDto, OAuthRedirectDto
from clients.application.dto.auth.register_request_dto import RegisterRequestDto
from clients.application.dto.auth.verify_request_dto import VerifyRequestDto
from statements.oauth_scope import (
    PROVIDER,
    fake_authorization_code,
    query_param,
    unique_email,
    unique_subject,
)

SESSION_FIELDS = (
    "access_token",
    "refresh_token",
    "access_token_expires_at",
    "refresh_token_expires_at",
)

PASSWORD_ACCOUNT_PASSWORD = "Str0ng!Pass"


def account_id_of(response: OAuthExchangeResponseDto) -> str:
    """The `sub` claim of the issued access token, decoded WITHOUT verification.

    The test is not authenticating anything — it only needs the account identity the
    backend resolved, and the signature is the backend's business. Padding is added
    back because JWT strips base64url '='.
    """
    payload = response.body["access_token"].split(".")[1]
    decoded = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
    return json.loads(decoded)["sub"]


class OAuthStatements:
    """Drives the three-leg handshake as a browser would: start, provider callback,
    exchange. Never calls a real provider — the backend under test runs the fake
    OAuth adapter behind the same port the Yandex adapter implements.
    """

    def __init__(self, client: ApplicationClient):
        self._client = client

    async def start(self, provider: str = PROVIDER) -> OAuthRedirectDto:
        return await self._client.oauth_start(provider)

    async def minted_state(self, provider: str = PROVIDER) -> str:
        redirect = await self.start(provider)
        assert redirect.status_code == 302, (
            f"setup: expected /start to redirect, got {redirect.status_code}"
        )
        state = query_param(redirect.location, "state")
        assert state, f"setup: expected a server-minted state in {redirect.location}"
        return state

    async def callback(self, provider: str = PROVIDER, **params) -> OAuthRedirectDto:
        return await self._client.oauth_callback(provider, params)

    async def completed_callback(
        self, subject: str | None = None, email: str | None = None
    ) -> OAuthRedirectDto:
        state = await self.minted_state()
        return await self.callback(
            code=fake_authorization_code(
                subject or unique_subject(), email or unique_email()
            ),
            state=state,
        )

    async def handoff_code(self, subject: str | None = None, email: str | None = None) -> str:
        redirect = await self.completed_callback(subject=subject, email=email)
        assert redirect.status_code == 302, (
            f"setup: expected /callback to redirect, got {redirect.status_code} "
            f"location={redirect.location}"
        )
        code = query_param(redirect.location, "code")
        assert code, f"setup: expected a handoff code in {redirect.location}"
        return code

    async def exchange(self, code: str) -> OAuthExchangeResponseDto:
        return await self._client.oauth_exchange({"code": code})

    async def exchange_raw(self, body: dict) -> OAuthExchangeResponseDto:
        return await self._client.oauth_exchange(body)

    async def exchange_twice_concurrently(
        self, code: str
    ) -> tuple[OAuthExchangeResponseDto, OAuthExchangeResponseDto]:
        # Genuinely concurrent, not sequential: the invariant under test is the
        # atomicity of the redeem, and a sequential pair would pass even against a
        # read-then-write implementation that loses the race in production.
        first, second = await asyncio.gather(self.exchange(code), self.exchange(code))
        return first, second

    async def signed_in_session(self) -> OAuthExchangeResponseDto:
        return await self.exchange(await self.handoff_code())

    async def given_password_account(self) -> tuple[str, str]:
        email = f"password-{uuid.uuid4()}@example.com"
        register = await self._client.register(
            RegisterRequestDto(
                email=email,
                password=PASSWORD_ACCOUNT_PASSWORD,
                confirm_password=PASSWORD_ACCOUNT_PASSWORD,
            )
        )
        code = register.body.get("verification_code")
        assert code, f"setup: registration issued no verification code, body={register.body}"
        verify = await self._client.verify(VerifyRequestDto(email=email, code=code))
        assert verify.status_code == 200, f"setup: verification failed ({verify.status_code})"
        return email, PASSWORD_ACCOUNT_PASSWORD

    async def can_still_log_in_with_password(self, email: str, password: str) -> bool:
        response = await self._client.login(LoginRequestDto(email=email, password=password))
        return response.status_code == 200

    async def start_from(self, headers: dict, provider: str = PROVIDER) -> OAuthRedirectDto:
        return await self._client.oauth_start(provider, headers=headers)

    async def callback_from(
        self, headers: dict, provider: str = PROVIDER, **params
    ) -> OAuthRedirectDto:
        return await self._client.oauth_callback(provider, params, headers=headers)

    async def exchange_from(self, headers: dict, code: str) -> OAuthExchangeResponseDto:
        return await self._client.oauth_exchange({"code": code}, headers=headers)
