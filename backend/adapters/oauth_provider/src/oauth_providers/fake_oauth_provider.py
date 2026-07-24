from urllib.parse import urlencode

from auth.oauth.oauth_provider import OAuthProviderError, ProviderIdentity


class FakeOAuthProvider:
    """Test/stend stand-in for a real provider, behind the same `OAuthProvider` port.

    It impersonates a named real provider (its `name` is the real slug, e.g.
    `yandex`) so routes and state binding behave exactly as in production, but it
    never leaves the host: `fetch_identity` reads the identity to assert straight
    out of the authorization code the caller handed to /callback, in the format
    `sub=<subject>;email=<email>`. This is what keeps every test run from reaching
    the real provider — structural typing against the port, mirroring `FakeProvider`.
    """

    def __init__(self, name: str, authorize_url: str, redirect_uri: str, client_id: str) -> None:
        self._name = name
        self._authorize_url = authorize_url
        self._redirect_uri = redirect_uri
        self._client_id = client_id

    @property
    def name(self) -> str:
        return self._name

    def authorization_url(self, state: str) -> str:
        query = urlencode(
            {
                "response_type": "code",
                "client_id": self._client_id,
                "redirect_uri": self._redirect_uri,
                "state": state,
            }
        )
        return f"{self._authorize_url}?{query}"

    async def fetch_identity(self, authorization_code: str) -> ProviderIdentity:
        fields = dict(part.split("=", 1) for part in authorization_code.split(";") if "=" in part)
        subject, email = fields.get("sub"), fields.get("email")
        if not subject or not email:
            raise OAuthProviderError(f"unreadable fake authorization code: {authorization_code!r}")
        return ProviderIdentity(subject=subject, email=email)
