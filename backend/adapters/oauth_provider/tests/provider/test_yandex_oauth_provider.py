import httpx
import pytest

from auth.oauth.oauth_provider import OAuthProviderError
from oauth_providers import yandex_oauth_provider
from oauth_providers.yandex_oauth_provider import YandexOAuthProvider

_REAL_ASYNC_CLIENT = httpx.AsyncClient


def _provider() -> YandexOAuthProvider:
    return YandexOAuthProvider(
        client_id="cid",
        client_secret="secret",
        redirect_uri="http://localhost/api/v1/auth/oauth/yandex/callback",
    )


def _install(monkeypatch, handler) -> None:
    def factory(*args, **kwargs):
        kwargs.pop("timeout", None)
        return _REAL_ASYNC_CLIENT(transport=httpx.MockTransport(handler))

    monkeypatch.setattr(yandex_oauth_provider.httpx, "AsyncClient", factory)


def _routes(token: dict | None = None, info: dict | None = None, token_status: int = 200):
    token = {"access_token": "AT", "token_type": "bearer"} if token is None else token
    info = {"id": "2027708195", "default_email": "user@yandex.ru"} if info is None else info

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/token"):
            return httpx.Response(token_status, json=token)
        return httpx.Response(200, json=info)

    return handler


class TestYandexAuthorizationUrl:
    def test_targets_the_yandex_authorize_endpoint_with_state(self):
        url = _provider().authorization_url("STATE123")

        assert url.startswith("https://oauth.yandex.ru/authorize?")
        assert "state=STATE123" in url
        assert "client_id=cid" in url


class TestYandexFetchIdentity:
    async def test_maps_id_and_default_email_to_the_identity(self, monkeypatch):
        _install(monkeypatch, _routes())

        identity = await _provider().fetch_identity("auth-code")

        assert identity.subject == "2027708195"
        assert identity.email == "user@yandex.ru"

    async def test_stringifies_a_numeric_subject(self, monkeypatch):
        _install(monkeypatch, _routes(info={"id": 2027708195, "default_email": "u@yandex.ru"}))

        identity = await _provider().fetch_identity("auth-code")

        assert identity.subject == "2027708195"

    async def test_raises_when_the_token_response_has_no_access_token(self, monkeypatch):
        _install(monkeypatch, _routes(token={"token_type": "bearer"}))

        with pytest.raises(OAuthProviderError):
            await _provider().fetch_identity("auth-code")

    async def test_raises_when_the_info_response_lacks_the_email(self, monkeypatch):
        _install(monkeypatch, _routes(info={"id": "2027708195"}))

        with pytest.raises(OAuthProviderError):
            await _provider().fetch_identity("auth-code")

    async def test_raises_when_the_token_endpoint_returns_an_error_status(self, monkeypatch):
        _install(monkeypatch, _routes(token={"error": "invalid_client"}, token_status=400))

        with pytest.raises(OAuthProviderError):
            await _provider().fetch_identity("auth-code")
