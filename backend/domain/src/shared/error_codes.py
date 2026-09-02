"""Every `error_code` this API answers with, as constants rather than literals.

A code is written twice: once where it is raised, once as a key in the rest
layer's status map (`error_handling/exception_handlers.py`). The map's default is
400, so a typo on either side does not fail -- it silently answers 400 for a
refusal meant to be 401, 409 or 429, and only a client notices. Two references to
one constant cannot drift that way.

It lives in the domain because that is the only layer every other one may import,
and the vocabulary is shared: `INVALID_IDEMPOTENCY_KEY` is raised by three
usecases across two slices, `UNAUTHORIZED` by a usecase and by the rest layer's
own token guard.

Each member's value is its own name, produced by `auto()` rather than written out
a second time. Two spellings of one code is how a rename becomes a silent
400: the raise site says `INVALID_LIMTI`, the status map says `INVALID_LIMIT`,
and nothing fails. It also keeps a credential scanner quiet -- `PASSWORD = "..."`
and `TOKEN = "..."` are the shape one looks for, and a security finding that is
really an error-code table costs the reader the same time as a real one.

Two slices keep their own modules -- `analytics.analytics_error_codes` and
`auth.oauth.oauth_error_codes` -- because those carry the fixed refusal MESSAGES
and, in OAuth's case, an exception type alongside the codes. The CODES themselves
are members here: those modules now bind names to enum members rather than to
bare strings, so `_ERROR_CODE_STATUS_MAP` is keyed by one type throughout. A dict
mixing enum members with raw strings looks equivalent -- `StrEnum` hashes like its
value -- right up to the point where a typo'd string key silently falls through to
the 400 default with nothing to compare it against.
"""

from enum import StrEnum, auto


class ErrorCode(StrEnum):
    """A `StrEnum`, so a member IS the wire string.

    It compares equal to the literal, serializes to it through `json.dumps`, and
    keys the rest layer's status dict -- nothing downstream has to know these
    stopped being plain constants.
    """

    @staticmethod
    def _generate_next_value_(
        name: str,
        start: int,  # noqa: ARG004 -- the signature is enum's, not ours
        count: int,  # noqa: ARG004
        last: list,  # noqa: ARG004
    ) -> str:
        return name

    # --- Registration and sign-in ---
    EMAIL_ALREADY_REGISTERED = auto()
    INVALID_PASSWORD = auto()
    PASSWORD_MISMATCH = auto()
    INVALID_CREDENTIALS = auto()
    INVALID_REFRESH_TOKEN = auto()
    ACCOUNT_LOCKED = auto()
    UNVERIFIED = auto()
    UNAUTHORIZED = auto()
    # The projects feed answers 401 with this one rather than UNAUTHORIZED, because
    # `projects_list.yaml` declares it. Kept distinct on purpose: the two are not
    # interchangeable to a client reading the spec.
    UNAUTHENTICATED = auto()

    # The per-source bound in front of the password routes, mapped to HTTP 429.
    # Distinct from OAUTH_RATE_LIMITED so a client can tell which bound refused it,
    # and it names the class of refusal only -- never the source or the count.
    AUTH_RATE_LIMITED = auto()

    # --- E-mail verification ---
    ALREADY_VERIFIED = auto()
    INVALID_CODE = auto()
    INVALID_OR_EXPIRED_CODE = auto()
    RESEND_COOLDOWN_ACTIVE = auto()

    # --- Documents ---
    INVALID_VERSION = auto()
    CONTENT_TOO_LONG = auto()
    CONVERTED_CONTENT_TOO_LONG = auto()
    DOCUMENT_CREATION_FAILED = auto()
    GENERATION_NOT_COMPLETED = auto()
    INVALID_FORMAT = auto()
    INVALID_DATE_RANGE = auto()

    # --- Generation ---
    INVALID_DOCUMENT_TYPE = auto()
    INVALID_TEXT_STYLE = auto()
    NOT_RETRYABLE = auto()
    RETRY_LIMIT_REACHED = auto()

    # --- Idempotency, shared by the document and generation slices ---
    INVALID_IDEMPOTENCY_KEY = auto()
    IDEMPOTENCY_KEY_REUSED = auto()

    # --- Paging and filtering, shared by every list route ---
    INVALID_PAGE = auto()
    INVALID_LIMIT = auto()
    INVALID_CURSOR = auto()
    INVALID_QUERY = auto()
    INVALID_SORT = auto()

    # --- OAuth, re-exported by `auth.oauth.oauth_error_codes` with its messages ---
    # The exchange answers ONE code for every "this code will not become a session"
    # reason -- unknown, already redeemed, expired, over-length. Distinguishing them
    # would tell an attacker which handoff codes ever existed.
    INVALID_OR_EXPIRED_OAUTH_CODE = auto()
    UNKNOWN_OAUTH_PROVIDER = auto()
    OAUTH_RATE_LIMITED = auto()

    # --- Analytics ingest, re-exported by `analytics.analytics_error_codes` ---
    UNKNOWN_EVENT_NAME = auto()
    INVALID_VISITOR_ID = auto()
    INVALID_OCCURRENCE_KEY = auto()
    OCCURRENCE_KEY_CONFLICT = auto()
    RATE_LIMITED = auto()
    REQUEST_BODY_TOO_LARGE = auto()
