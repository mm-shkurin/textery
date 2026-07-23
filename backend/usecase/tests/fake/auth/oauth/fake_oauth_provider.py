from auth.oauth.oauth_provider import OAuthProviderError, ProviderIdentity


class FakeOAuthProvider:
    """Usecase-test double for one provider, structurally satisfying the port.

    `fetch_identity` returns a preset identity, or raises `OAuthProviderError` when
    `raise_on_fetch` is set — letting a callback test drive both the happy path and a
    provider failure without any adapter or network.
    """

    def __init__(self, name: str = "yandex", identity: ProviderIdentity | None = None) -> None:
        self._name = name
        self.identity = identity or ProviderIdentity(subject="2027708195", email="user@yandex.ru")
        self.raise_on_fetch: Exception | None = None
        self.authorization_url_calls: list[str] = []
        self.fetch_calls: list[str] = []

    @property
    def name(self) -> str:
        return self._name

    def authorization_url(self, state: str) -> str:
        self.authorization_url_calls.append(state)
        return f"https://provider.example/authorize?state={state}"

    async def fetch_identity(self, authorization_code: str) -> ProviderIdentity:
        self.fetch_calls.append(authorization_code)
        if self.raise_on_fetch is not None:
            raise self.raise_on_fetch
        return self.identity


def failing_provider(name: str = "yandex") -> FakeOAuthProvider:
    provider = FakeOAuthProvider(name=name)
    provider.raise_on_fetch = OAuthProviderError("provider leg failed")
    return provider
