from typing import Protocol

from auth.oauth_identity import OAuthIdentity


class OAuthIdentityRepository(Protocol):
    """Persistence for the provider-asserted identity, keyed by (provider, subject).

    The key is the subject, never the email: a provider email can be renamed or
    reassigned, the subject cannot, so resolving on the subject is what keeps one
    person's account from being handed to another after a rename.
    """

    async def find(self, provider: str, subject: str) -> OAuthIdentity | None: ...

    async def save(self, identity: OAuthIdentity) -> None: ...
