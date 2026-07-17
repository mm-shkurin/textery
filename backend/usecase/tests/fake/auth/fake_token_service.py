from datetime import UTC, datetime, timedelta
from uuid import UUID

from auth.token_pair import TokenPair
from shared.exceptions import InvalidTokenException


class FakeTokenService:
    """In-memory `TokenService` double.

    Signing is not simulated: the real algorithm, expiry and claim-shape rules
    are `JwtTokenService`'s own tests to cover. What this double exists for is to
    record *whose* pair was issued, so a usecase test can prove the token was
    minted for the account that actually authenticated -- and to let a test drive
    `read_refresh_subject` down either branch without minting a real token.
    """

    ISSUED_AT = datetime(2026, 7, 16, 12, 0, 0, tzinfo=UTC)

    def __init__(self) -> None:
        self.issued_for: list[tuple[UUID, str]] = []
        self.refresh_subject: UUID | None = None
        self.raise_on_read_refresh_subject: Exception | None = None
        self.read_refresh_subject_call_count = 0

    def issue_pair(self, account_id: UUID, email: str) -> TokenPair:
        self.issued_for.append((account_id, email))
        # Tokens carry the account id so a test can tell one account's pair from
        # another's -- a constant string would pass even if the usecase issued
        # the pair for the wrong account.
        return TokenPair(
            access_token=f"access-token-for-{account_id}",
            refresh_token=f"refresh-token-for-{account_id}",
            access_token_expires_at=self.ISSUED_AT + timedelta(minutes=15),
            refresh_token_expires_at=self.ISSUED_AT + timedelta(days=7),
        )

    def read_refresh_subject(self, refresh_token: str) -> UUID:
        self.read_refresh_subject_call_count += 1
        if self.raise_on_read_refresh_subject is not None:
            raise self.raise_on_read_refresh_subject
        if self.refresh_subject is None:
            raise InvalidTokenException("refresh token is not valid")
        return self.refresh_subject
