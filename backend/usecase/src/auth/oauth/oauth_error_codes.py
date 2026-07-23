from shared.exceptions import DomainException

# The exchange answers exactly one code for every "this code will not become a
# session" reason — unknown, already redeemed, expired, over-length. Distinguishing
# them would tell an attacker which handoff codes ever existed.
INVALID_OR_EXPIRED_OAUTH_CODE = "INVALID_OR_EXPIRED_OAUTH_CODE"

UNKNOWN_OAUTH_PROVIDER = "UNKNOWN_OAUTH_PROVIDER"

# The value placed in the frontend redirect's `?error=` on any failed callback. It
# is a fixed, client-safe token, never the internal reason: which leg failed (forged
# state, provider error, an email already owned by a password account) is operator
# information, and rendering it raw is the exact leak Security 2.1 names.
OAUTH_CALLBACK_FAILED = "oauth_failed"


class OAuthCallbackError(DomainException):
    """Any reason the callback cannot mint a handoff code.

    One exception for every cause on purpose: the callback answers the same generic
    `?error=` redirect for all of them, so the caller never branches on which failed.
    """
