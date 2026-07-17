from typing import Optional

from shared.exceptions import ValidationException
from shared.keyset_cursor import INVALID_CURSOR_MESSAGE, KeysetCursor

MIN_LIMIT = 1
MAX_LIMIT = 100
DEFAULT_LIMIT = 20

INVALID_LIMIT_MESSAGE = f"limit must be between {MIN_LIMIT} and {MAX_LIMIT}."


class PageRequest:
    """A validated `?limit=&cursor=` pair.

    Lives in the domain rather than as Pydantic `Query(ge=1, le=100)` constraints
    for the reason IdempotencyKey gives: a violation must surface as this
    project's `{error_code, message}` shape, not Pydantic's envelope. It is shared
    by every history list so the bounds cannot drift between them.
    """

    def __init__(self, limit: int = DEFAULT_LIMIT, cursor: Optional[str] = None) -> None:
        self.limit = self._validated_limit(limit)
        self.cursor = self._decoded(cursor)

    @property
    def fetch_size(self) -> int:
        """One more row than asked for -- the has-next probe.

        Reading a single extra row answers "is there another page" without a
        COUNT, which under keyset would have to scan exactly what the cursor
        exists to avoid.
        """
        return self.limit + 1

    @staticmethod
    def _validated_limit(limit: int) -> int:
        # bool before int: bool subclasses int, so JSON `true` would otherwise pass
        # as limit=1 rather than being rejected.
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise ValidationException(error_code="INVALID_LIMIT", message=INVALID_LIMIT_MESSAGE)
        if limit < MIN_LIMIT or limit > MAX_LIMIT:
            raise ValidationException(error_code="INVALID_LIMIT", message=INVALID_LIMIT_MESSAGE)
        return limit

    @staticmethod
    def _decoded(cursor: Optional[str]) -> Optional[KeysetCursor]:
        if cursor is None:
            return None
        try:
            return KeysetCursor.decode(cursor)
        except ValueError as error:
            raise ValidationException(
                error_code="INVALID_CURSOR", message=INVALID_CURSOR_MESSAGE
            ) from error


class Page:
    """One page of history plus the anchor for the next, if any."""

    def __init__(self, items: list, next_cursor: Optional[str]) -> None:
        self.items = items
        self.next_cursor = next_cursor

    @classmethod
    def of(cls, rows: list, limit: int) -> "Page":
        """Trim the has-next probe row and derive the next cursor from what remains.

        `next_cursor` is None on the last page -- deliberately, rather than always
        emitting one. A client that stops only when the cursor is null would
        otherwise loop forever on an empty final page.
        """
        has_more = len(rows) > limit
        items = rows[:limit]
        next_cursor = KeysetCursor.of(items[-1]).encode() if has_more and items else None
        return cls(items=items, next_cursor=next_cursor)
