import pytest

from auth.oauth.oauth_provider import OAuthProviderError
from oauth_providers.fake_oauth_provider import FakeOAuthProvider


def _provider() -> FakeOAuthProvider:
    return FakeOAuthProvider(
        name="yandex",
        authorize_url="https://fake-oauth.local/authorize",
        redirect_uri="http://localhost/api/v1/auth/oauth/yandex/callback",
        client_id="cid",
    )


class TestFakeOAuthProviderAuthorizationUrl:
    def test_carries_the_state_and_client_id(self):
        url = _provider().authorization_url("STATE123")

        assert url.startswith("https://fake-oauth.local/authorize?")
        assert "state=STATE123" in url
        assert "client_id=cid" in url


class TestFakeOAuthProviderFetchIdentity:
    async def test_parses_the_subject_and_email_from_the_code(self):
        identity = await _provider().fetch_identity("sub=2027708195;email=user@yandex.ru")

        assert identity.subject == "2027708195"
        assert identity.email == "user@yandex.ru"

    async def test_rejects_a_code_missing_the_subject(self):
        with pytest.raises(OAuthProviderError):
            await _provider().fetch_identity("email=user@yandex.ru")

    async def test_rejects_a_code_missing_the_email(self):
        with pytest.raises(OAuthProviderError):
            await _provider().fetch_identity("sub=2027708195")

    async def test_rejects_an_unstructured_code(self):
        with pytest.raises(OAuthProviderError):
            await _provider().fetch_identity("garbage")
