from shared.error_codes import ErrorCode
from shared.exceptions import DomainException

# The codes are `ErrorCode` members, bound here under the names this slice raises
# them by. One vocabulary, so the rest layer's status map has a single key type;
# the local names stay because this module is also where the fixed MESSAGES live,
# and a raise site reading `oauth_error_codes.OAUTH_RATE_LIMITED` says which slice
# owns the refusal.

# The exchange answers exactly one code for every "this code will not become a
# session" reason — unknown, already redeemed, expired, over-length. Distinguishing
# them would tell an attacker which handoff codes ever existed.
INVALID_OR_EXPIRED_OAUTH_CODE = ErrorCode.INVALID_OR_EXPIRED_OAUTH_CODE

UNKNOWN_OAUTH_PROVIDER = ErrorCode.UNKNOWN_OAUTH_PROVIDER

# Returned when a source exceeds the per-window rate on any of the three OAuth legs.
# Mapped to HTTP 429 (abuse bound, hazard-scan G6 / Security 5.1). It names the class
# of refusal, never the source or the count — nothing an attacker can probe with.
OAUTH_RATE_LIMITED = ErrorCode.OAUTH_RATE_LIMITED

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
