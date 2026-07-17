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

    def read_access_subject(self, access_token: str) -> UUID:
        """Return the account id carried by a valid access token.

        Added, not modified: `read_refresh_subject` rejects access tokens by
        design, so before this there was no way to identify the caller behind an
        `Authorization: Bearer` header, and no route read one.

        Same failure contract as its refresh twin -- one `InvalidTokenException`
        for expired, tampered, wrong-key, wrong-type, and malformed alike. The
        wrong-type half matters most here: both tokens are signed with the same
        key, so without a `type` check a 7-day refresh token would be accepted as
        a document credential.
        """
        ...
