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

Two slices keep their own modules -- `analytics.analytics_error_codes` and
`auth.oauth.oauth_error_codes` -- because those carry the fixed refusal MESSAGES
and, in OAuth's case, an exception type alongside the codes. This file is the
codes that had no home at all.
"""

# --- Registration and sign-in ---
EMAIL_ALREADY_REGISTERED = "EMAIL_ALREADY_REGISTERED"
INVALID_PASSWORD = "INVALID_PASSWORD"
PASSWORD_MISMATCH = "PASSWORD_MISMATCH"
INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
INVALID_REFRESH_TOKEN = "INVALID_REFRESH_TOKEN"
ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
UNVERIFIED = "UNVERIFIED"
UNAUTHORIZED = "UNAUTHORIZED"
# The projects feed answers 401 with this one rather than UNAUTHORIZED, because
# `projects_list.yaml` declares it. Kept distinct on purpose: the two are not
# interchangeable to a client reading the spec.
UNAUTHENTICATED = "UNAUTHENTICATED"

# --- E-mail verification ---
ALREADY_VERIFIED = "ALREADY_VERIFIED"
INVALID_CODE = "INVALID_CODE"
INVALID_OR_EXPIRED_CODE = "INVALID_OR_EXPIRED_CODE"
RESEND_COOLDOWN_ACTIVE = "RESEND_COOLDOWN_ACTIVE"

# --- Documents ---
INVALID_VERSION = "INVALID_VERSION"
CONTENT_TOO_LONG = "CONTENT_TOO_LONG"
CONVERTED_CONTENT_TOO_LONG = "CONVERTED_CONTENT_TOO_LONG"
DOCUMENT_CREATION_FAILED = "DOCUMENT_CREATION_FAILED"
GENERATION_NOT_COMPLETED = "GENERATION_NOT_COMPLETED"
INVALID_FORMAT = "INVALID_FORMAT"
INVALID_DATE_RANGE = "INVALID_DATE_RANGE"

# --- Generation ---
INVALID_DOCUMENT_TYPE = "INVALID_DOCUMENT_TYPE"
INVALID_TEXT_STYLE = "INVALID_TEXT_STYLE"
NOT_RETRYABLE = "NOT_RETRYABLE"
RETRY_LIMIT_REACHED = "RETRY_LIMIT_REACHED"

# --- Idempotency, shared by the document and generation slices ---
INVALID_IDEMPOTENCY_KEY = "INVALID_IDEMPOTENCY_KEY"
IDEMPOTENCY_KEY_REUSED = "IDEMPOTENCY_KEY_REUSED"

# --- Paging and filtering, shared by every list route ---
INVALID_PAGE = "INVALID_PAGE"
INVALID_LIMIT = "INVALID_LIMIT"
INVALID_CURSOR = "INVALID_CURSOR"
INVALID_QUERY = "INVALID_QUERY"
INVALID_SORT = "INVALID_SORT"
