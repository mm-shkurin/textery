from datetime import timedelta
from uuid import UUID

import jwt

from auth.token_pair import TokenPair
from shared.clock import Clock, SystemClock
from shared.exceptions import InvalidTokenException

_ALGORITHM = "HS256"
_ACCESS_TTL = timedelta(minutes=15)
_REFRESH_TTL = timedelta(days=7)
_ACCESS_TYPE = "access"
_REFRESH_TYPE = "refresh"


class JwtTokenService:
    """JWT implementation of the `TokenService` port.

    Stateless: refresh tokens are not persisted, so there is **no revocation** --
    a leaked refresh token stays usable until it expires. Accepted deliberately
    under sprint-1's deadline and recorded here rather than discovered later.
    Scenario 6.3 asks for a token that "does not correspond to any issued token"
    to be rejected, which stateless signatures cannot answer: a validly signed
    token always corresponds. What is enforced is expiry, signature, and token
    type. Closing the gap means a refresh_tokens table -- scenario 6.1a's job.
    """

    def __init__(self, secret: str, clock: Clock | None = None) -> None:
        # No default secret, deliberately: a fallback here would ship a signing key
        # that is public in the git history, and every token in production would be
        # forgeable by anyone who read the repo.
        if not secret:
            raise ValueError("JWT signing secret must not be empty")
        self._secret = secret
        self._clock = clock or SystemClock()

    def issue_pair(self, account_id: UUID, email: str) -> TokenPair:
        now = self._clock.now()
        access_expires_at = now + _ACCESS_TTL
        refresh_expires_at = now + _REFRESH_TTL
        return TokenPair(
            access_token=self._encode(account_id, email, _ACCESS_TYPE, now, access_expires_at),
            refresh_token=self._encode(account_id, email, _REFRESH_TYPE, now, refresh_expires_at),
            access_token_expires_at=access_expires_at,
            refresh_token_expires_at=refresh_expires_at,
        )

    def read_refresh_subject(self, refresh_token: str) -> UUID:
        try:
            claims = jwt.decode(refresh_token, self._secret, algorithms=[_ALGORITHM])
        except jwt.PyJWTError as error:
            # Covers expiry, bad signature, a key rotated out from under it, and
            # malformed input alike -- all the same answer to the client.
            raise InvalidTokenException("refresh token is not valid") from error
        # An access token is signed by the same key, so without this check it would
        # be accepted at /refresh and a 15-minute credential would silently become
        # a 7-day one.
        if claims.get("type") != _REFRESH_TYPE:
            raise InvalidTokenException("refresh token is not valid")
        try:
            return UUID(claims["sub"])
        except (KeyError, ValueError) as error:
            # A token whose claim shape no longer matches current code must be a
            # clean rejection, never an unhandled crash (scenario 6.4).
            raise InvalidTokenException("refresh token is not valid") from error

    def _encode(self, account_id, email, token_type, issued_at, expires_at) -> str:
        return jwt.encode(
            {
                "sub": str(account_id),
                "email": email,
                "type": token_type,
                "iat": issued_at,
                "exp": expires_at,
            },
            self._secret,
            algorithm=_ALGORITHM,
        )
