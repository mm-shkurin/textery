"""The narrowing a history request may apply: a text query and a creation-date window.

A value object rather than three loose parameters threaded through the usecase and
the storage, for the reason `ProjectPageRequest` is one: the rules — how a blank
query differs from an absent one, which date formats are accepted, that a window
must not be inverted — are asked once, at construction, and every layer below
holds something already proven valid.

An empty or whitespace-only value is folded down to absence rather than refused,
and the two ends of that decision sit in different layers. HERE, `?q=` answers the
unfiltered feed: a user who clears the search box, or tabs through a date input
without picking anything, is asking for their whole history, and a 400 for that is
a refusal of the most ordinary action on the screen.

The guard against a search that LOOKS active while matching everything belongs to
the client, which omits the parameter entirely rather than sending it empty — see
`withFilter` in `frontend/src/features/history/api/historyApi.ts`. Verified against
the running stack 2026-08-20: `GET /api/v1/documents?q=` answers 200 with the full
feed.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time

from shared import error_codes, limits
from shared.exceptions import ValidationException

MAX_QUERY_LENGTH = limits.MAX_QUERY_LENGTH
QUERY_TOO_LONG_MESSAGE = f"q must be at most {MAX_QUERY_LENGTH} characters"
INVALID_DATE_MESSAGE = "date must be an ISO-8601 date (YYYY-MM-DD) or datetime"
_DAY_END = time(23, 59, 59, 999999)

INVERTED_WINDOW_MESSAGE = "created_from must not be later than created_to"


def _parse_boundary(raw: str | None, name: str, *, end_of_day: bool) -> datetime | None:
    """One end of the window, as an aware UTC instant, or `None` when omitted.

    A bare `YYYY-MM-DD` is what the date input on the history screen sends, and the two ends read
    it differently on purpose: `created_from=2026-08-20` means from that day's first instant,
    `created_to=2026-08-20` through its last. Read both as midnight and «с 20 по 20 августа»
    matches nothing — the single-day filter a user is most likely to ask for would be the one
    query that always comes back empty.

    The date-only case is recognised by ASKING `date.fromisoformat` FIRST, not by waiting for
    `datetime.fromisoformat` to fail on it. It does not fail: since 3.11 it accepts a bare date and
    returns midnight, so an except-branch holding the widening is a branch that never runs — the
    end-of-day rule would be dead code that reads as if it were live.

    A naive datetime is read as UTC rather than refused: `created_at` is stored aware-UTC, and
    comparing it against a naive bound raises inside the driver — a 500 for what is a client
    mistake at worst.
    """
    if raw is None or raw == "":
        return None

    parsed = _as_datetime(raw, name, end_of_day=end_of_day)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _as_datetime(raw: str, name: str, *, end_of_day: bool) -> datetime:
    """The raw value as a datetime, widened to the day's end when it named a date and nothing else.

    `end_of_day` is passed in rather than derived from `name`: which end widens is the caller's
    rule, and a function that inspects the parameter's NAME to decide semantics is one rename away
    from silently reading every boundary as a start.
    """
    try:
        day = date.fromisoformat(raw)
    except ValueError:
        pass
    else:
        return datetime.combine(day, _DAY_END if end_of_day else datetime.min.time())

    try:
        return datetime.fromisoformat(raw)
    except ValueError as error:
        raise ValidationException(
            error_code=f"INVALID_{name.upper()}", message=INVALID_DATE_MESSAGE
        ) from error


@dataclass(frozen=True)
class DocumentFilter:
    """A parsed, validated narrowing. `EMPTY` is the unfiltered feed."""

    query: str | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None

    @property
    def is_empty(self) -> bool:
        return self.query is None and self.created_from is None and self.created_to is None

    @classmethod
    def parse(
        cls,
        q: str | None = None,
        created_from: str | None = None,
        created_to: str | None = None,
    ) -> "DocumentFilter":
        query = None
        if q is not None:
            if len(q) > MAX_QUERY_LENGTH:
                raise ValidationException(
                    error_code=error_codes.INVALID_QUERY, message=QUERY_TOO_LONG_MESSAGE
                )
            # Trimmed, then folded to absent when nothing visible remains: a query
            # of spaces is a user who has not typed anything yet, and matching
            # titles against " " would empty the screen while they think.
            trimmed = q.strip()
            query = trimmed or None

        start = _parse_boundary(created_from, "created_from", end_of_day=False)
        end = _parse_boundary(created_to, "created_to", end_of_day=True)
        if start is not None and end is not None and start > end:
            raise ValidationException(
                error_code=error_codes.INVALID_DATE_RANGE, message=INVERTED_WINDOW_MESSAGE
            )
        return cls(query=query, created_from=start, created_to=end)


EMPTY = DocumentFilter()
