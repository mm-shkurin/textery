from datetime import datetime, timedelta
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

# RFC 7518 §3.2: an HS256 key must be at least as long as the SHA-256 output.
MIN_SECRET_BYTES = 32


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
        #
        # Length is checked too, not just emptiness. HS256's security rests
        # entirely on the key being unguessable, and RFC 7518 §3.2 requires a key
        # at least as long as the hash output -- 32 bytes for SHA-256. A shorter
        # one is brute-forceable offline from a single captured token, which
        # yields forged access *and* refresh tokens for any account. The check
        # runs at boot (see container/runtime.py), so a deployment configured with
        # `JWT_SECRET=change-me` fails immediately and loudly rather than serving
        # traffic that looks fine and isn't.
        if len(secret.encode("utf-8")) < MIN_SECRET_BYTES:
            raise ValueError(
                f"JWT signing secret must be at least {MIN_SECRET_BYTES} bytes "
                f"(RFC 7518 §3.2 for {_ALGORITHM}); generate one with: openssl rand -hex 32"
            )
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
        return self._read_subject(refresh_token, _REFRESH_TYPE, "refresh token is not valid")

    def read_access_subject(self, access_token: str) -> UUID:
        return self._read_subject(access_token, _ACCESS_TYPE, "access token is not valid")

    def _read_subject(self, token: str, expected_type: str, failure_message: str) -> UUID:
        try:
            claims = jwt.decode(token, self._secret, algorithms=[_ALGORITHM])
        except jwt.PyJWTError as error:
            # Covers expiry, bad signature, a key rotated out from under it, and
            # malformed input alike -- all the same answer to the client.
            raise InvalidTokenException(failure_message) from error
        # Both tokens are signed with the same key, so the type claim is the only
        # thing separating them. Without this check each is accepted where the
        # other belongs: a 15-minute access token would become a 7-day one at
        # /refresh, and a 7-day refresh token would become a document credential
        # at /documents.
        if claims.get("type") != expected_type:
            raise InvalidTokenException(failure_message)
        try:
            return UUID(claims["sub"])
        except (KeyError, ValueError) as error:
            # A token whose claim shape no longer matches current code must be a
            # clean rejection, never an unhandled crash (scenario 6.4).
            raise InvalidTokenException(failure_message) from error

    def _encode(
        self,
        account_id: UUID,
        email: str,
        token_type: str,
        issued_at: datetime,
        expires_at: datetime,
    ) -> str:
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
