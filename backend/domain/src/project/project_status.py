from datetime import datetime, timedelta

from generation.generation import (
    COMPLETED_STATUS,
    FAILED_STATUS,
    IN_PROGRESS_STATUS,
    PENDING_STATUS,
)

DOCUMENT_KIND = "document"
GENERATION_KIND = "generation"

# The contract's fail-closed member. A status this build does not know maps here
# and is never mapped onto a displayed one: a new status added by another story
# must not silently render as "готово".
UNKNOWN_STATUS = "unknown"

# Non-terminal past the stale threshold. The sweep is re-running the row, so the
# feed says so instead of showing it as running forever -- and offers no retry,
# because retrying live work runs it twice.
RECOVERING_STATUS = "recovering"

_NON_TERMINAL = frozenset({PENDING_STATUS, IN_PROGRESS_STATUS})
_KNOWN_GENERATION_STATUSES = _NON_TERMINAL | {COMPLETED_STATUS, FAILED_STATUS}


def generation_feed_status(
    stored_status: str,
    updated_at: datetime,
    now: datetime,
    stale_after: timedelta,
) -> str:
    """The status a generation row reports in the feed.

    A row this build does not recognise fails closed to `unknown` rather than
    being passed through: passing it through would let a status added elsewhere
    reach a client that maps it onto a displayed label by accident.

    The stale comparison is `>=`, so the label flips exactly *at* the threshold
    rather than one tick past it, and it is computed against an injected `now`
    rather than a direct system-time read -- the boundary is otherwise untestable.
    """
    if stored_status not in _KNOWN_GENERATION_STATUSES:
        return UNKNOWN_STATUS
    if stored_status in _NON_TERMINAL and now - updated_at >= stale_after:
        return RECOVERING_STATUS
    return stored_status


def generation_is_retryable(feed_status: str) -> bool:
    """Whether the feed offers «Повторить» on a row.

    Only a `failed` generation. A pending, in-progress or recovering row is not
    retryable -- the stale sweep requeues it, and a retry there duplicates work
    that is still running. `unknown` is not retryable either: that is the whole
    point of failing closed.

    Server-computed, and deliberately not derivable by the client: a client
    computing this from an enum it may not fully know would offer the button on
    an unrecognised status, which is fail-open.
    """
    return feed_status == FAILED_STATUS
