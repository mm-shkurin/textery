from typing import Protocol

from auth.oauth_state import OAuthState


class OAuthStateRepository(Protocol):
    """Persistence for the CSRF state, so it survives across the two request legs
    (/start mints it, /callback consumes it) and across instances — the callback can
    land on a different backend instance than the start did.
    """

    async def save(self, state: OAuthState) -> None: ...

    async def consume(self, value: str) -> OAuthState | None:
        """Atomically remove and return the state with this value, or None.

        Remove-on-read is what makes the state single-use: a replayed callback finds
        nothing to consume and is refused. The delete and the read are one statement
        so two legs racing the same state cannot both come away with it.
        """
        ...
