import logging
from urllib.parse import urlencode

import httpx

from auth.oauth.oauth_provider import OAuthProviderError, ProviderIdentity

logger = logging.getLogger(__name__)

AUTHORIZE_URL = "https://oauth.yandex.ru/authorize"
TOKEN_URL = "https://oauth.yandex.ru/token"
INFO_URL = "https://login.yandex.ru/info"


class YandexOAuthProvider:
    """Real Yandex ID adapter, behind the `OAuthProvider` port.

    `authorization_url` sends the browser to Yandex; `fetch_identity` trades the
    returned code for a token, then reads the account info. Any non-2xx or unreadable
    response becomes a single `OAuthProviderError` — which leg of the provider call
    failed is operator information, not something the client is told.
    """

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri

    @property
    def name(self) -> str:
        return "yandex"

    def authorization_url(self, state: str) -> str:
        query = urlencode(
            {
                "response_type": "code",
                "client_id": self._client_id,
                "redirect_uri": self._redirect_uri,
                "state": state,
            }
        )
        return f"{AUTHORIZE_URL}?{query}"

    async def fetch_identity(self, authorization_code: str) -> ProviderIdentity:
        async with httpx.AsyncClient(timeout=10.0) as client:
            access_token = await self._exchange_code(client, authorization_code)
            return await self._read_identity(client, access_token)

    async def _exchange_code(self, client: httpx.AsyncClient, code: str) -> str:
        response = await self._post(
            client,
            TOKEN_URL,
            {
                "grant_type": "authorization_code",
                "code": code,
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
        )
        token = response.get("access_token")
        if not token:
            # Keys only, never values — the token/secret must never reach a log (I5).
            logger.warning("Yandex token response had no access_token; keys=%s", list(response))
            raise OAuthProviderError("Yandex token response carried no access_token")
        return token

    async def _read_identity(self, client: httpx.AsyncClient, access_token: str) -> ProviderIdentity:
        try:
            response = await client.get(
                INFO_URL,
                params={"format": "json"},
                headers={"Authorization": f"OAuth {access_token}"},
            )
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPStatusError as error:
            logger.warning(
                "Yandex info request failed: %s %s", error.response.status_code, error.response.text
            )
            raise OAuthProviderError("Yandex info request failed") from error
        except (httpx.HTTPError, ValueError) as error:
            logger.warning("Yandex info request failed: %r", error)
            raise OAuthProviderError("Yandex info request failed") from error
        subject, email = body.get("id"), body.get("default_email")
        if not subject or not email:
            # Keys only, not values — this tells us whether the app was granted the
            # email scope without writing the address itself to a log (I5).
            logger.warning("Yandex info response missing id/default_email; keys=%s", list(body))
            raise OAuthProviderError("Yandex info response was missing id or default_email")
        return ProviderIdentity(subject=str(subject), email=email)

    async def _post(self, client: httpx.AsyncClient, url: str, data: dict) -> dict:
        try:
            response = await client.post(url, data=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as error:
            # The provider's error body (`{"error": ..., "error_description": ...}`)
            # is operator diagnostics — it carries no token and never our client
            # secret. Logged so a live-Yandex misconfig is visible; the caller still
            # answers a single generic error.
            logger.warning(
                "Yandex token request failed: %s %s", error.response.status_code, error.response.text
            )
            raise OAuthProviderError("Yandex token request failed") from error
        except (httpx.HTTPError, ValueError) as error:
            logger.warning("Yandex token request failed: %r", error)
            raise OAuthProviderError("Yandex token request failed") from error
