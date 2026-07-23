from dataclasses import dataclass
from typing import Protocol


class OAuthProviderError(Exception):
    """The provider leg failed: network, non-2xx, or an unreadable response."""


class OAuthConfigurationError(Exception):
    """The provider is not configured. Raised at boot, never answered lazily per request."""


@dataclass(frozen=True)
class ProviderIdentity:
    """What a provider asserts about the person who just signed in.

    Only the subject and the email: nothing a caller supplies can widen this, which
    is what keeps auto-create from over-binding on client-controlled fields.
    """

    subject: str
    email: str


class OAuthProvider(Protocol):
    """Port for one OAuth provider (Yandex ID, VK ID, ...).

    Mirrors `GenerationProvider`: the usecase depends on this Protocol only, adapters
    implement it, and tests bind a fake so no test run ever reaches a real provider.
    """

    @property
    def name(self) -> str:
        """Provider slug as it appears in the route (`yandex`, `vk`)."""
        ...

    def authorization_url(self, state: str) -> str:
        """The provider page to send the browser to, carrying the server-minted state."""
        ...

    async def fetch_identity(self, authorization_code: str) -> ProviderIdentity:
        """Trade the provider's authorization code for the asserted identity.

        Raises `OAuthProviderError` on any failure. The caller answers the same generic
        error for all of them: which leg failed is operator information, not client
        information.
        """
        ...
