from collections.abc import Iterable

from auth.oauth.oauth_error_codes import UNKNOWN_OAUTH_PROVIDER
from auth.oauth.oauth_provider import OAuthProvider
from shared.exceptions import ValidationException


class ProviderRegistry:
    """The set of OAuth providers this deployment actually serves, keyed by slug.

    A route slug (`yandex`, `vk`) resolves to a provider only if one was wired for
    it. `vk` with no credentials is simply absent, so it answers a named
    "unknown provider" error rather than being silently defaulted to another
    provider's handshake.
    """

    def __init__(self, providers: Iterable[OAuthProvider]) -> None:
        self._by_name = {provider.name: provider for provider in providers}

    def get(self, name: str) -> OAuthProvider:
        provider = self._by_name.get(name)
        if provider is None:
            raise ValidationException(
                f"no OAuth provider is configured for '{name}'", UNKNOWN_OAUTH_PROVIDER
            )
        return provider
