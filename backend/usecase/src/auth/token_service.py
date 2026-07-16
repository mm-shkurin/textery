from typing import Protocol
from uuid import UUID

from auth.token_pair import TokenPair


class TokenService(Protocol):
    """Port for issuing and reading auth tokens."""

    def issue_pair(self, account_id: UUID, email: str) -> TokenPair:
        ...

    def read_refresh_subject(self, refresh_token: str) -> UUID:
        """Return the account id carried by a valid refresh token.

        Raises `InvalidTokenException` when the token is expired, tampered with,
        signed by another key, not a refresh token, or shaped unlike what current
        code expects. Every one of those is the same answer to the client, so the
        caller never has to tell them apart.
        """
        ...
