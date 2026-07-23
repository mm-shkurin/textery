from auth.oauth_identity import OAuthIdentity


class FakeOAuthIdentityRepository:
    """In-memory `OAuthIdentityRepository`, keyed by (provider, subject)."""

    def __init__(self) -> None:
        self.saved: list[OAuthIdentity] = []

    async def find(self, provider: str, subject: str) -> OAuthIdentity | None:
        return next(
            (i for i in self.saved if i.provider == provider and i.subject == subject), None
        )

    async def save(self, identity: OAuthIdentity) -> None:
        self.saved.append(identity)
