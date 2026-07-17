from datetime import datetime, timezone

from auth.token_pair import TokenPair

ACCESS_TOKEN = "access.jwt.token"
REFRESH_TOKEN = "refresh.jwt.token"
ACCESS_EXPIRES_AT = datetime(2026, 7, 17, 12, 15, 0, tzinfo=timezone.utc)
REFRESH_EXPIRES_AT = datetime(2026, 7, 24, 12, 0, 0, tzinfo=timezone.utc)

EXPECTED_TOKEN_PAIR_BODY = {
    "access_token": ACCESS_TOKEN,
    "refresh_token": REFRESH_TOKEN,
    "access_token_expires_at": "2026-07-17T12:15:00Z",
    "refresh_token_expires_at": "2026-07-24T12:00:00Z",
}


def given_issued_token_pair() -> TokenPair:
    """The pair a usecase hands back on success. Access and refresh carry
    distinct values and distinct expiries, so a route that returns one where the
    other belongs — or copies one expiry onto both fields — fails the assertion
    instead of passing on symmetric placeholders.
    """
    return TokenPair(
        access_token=ACCESS_TOKEN,
        refresh_token=REFRESH_TOKEN,
        access_token_expires_at=ACCESS_EXPIRES_AT,
        refresh_token_expires_at=REFRESH_EXPIRES_AT,
    )
