import base64
import binascii
from datetime import datetime
from uuid import UUID

_SEPARATOR = "|"

INVALID_CURSOR_MESSAGE = "The cursor is not valid."


class KeysetCursor:
    """Opaque pagination anchor: the (created_at, id) of the last row of a page.

    Shared by every owner-scoped history list -- generations and documents both
    key on the same immutable pair, so one cursor serves both rather than two
    identical classes drifting apart.

    Keyset, not offset. OFFSET makes the database count and discard every skipped
    row, so page N costs O(N); worse, a row inserted while the user pages shifts
    the window and silently repeats or drops an item. An anchor tied to the last
    row read has neither problem: history grows at the newest end, which is the
    end the cursor is furthest from.

    `id` is part of the key, not decoration. `created_at` alone is not unique --
    two rows written in the same microsecond make the anchor ambiguous, and a page
    boundary landing between them drops or repeats one. The pair is total.

    **Sorted on created_at, never updated_at**, even for a "recently edited" list.
    A keyset anchor must be immutable: if the sort column can change under a
    paging client, the row it anchors to can move behind the cursor and be served
    twice, or ahead of it and never be served. created_at cannot move.

    Base64 of "<iso8601>|<uuid>". Opaque by contract, NOT by protection: it is
    trivially decodable and forgeable. That is harmless -- a forged cursor only
    moves the window within the caller's own rows, because the owner predicate is
    a separate AND in the query and is never read from the cursor. Do not put
    owner_id in this payload: that would turn a decorative value into an
    authorization input.
    """

    def __init__(self, created_at: datetime, id: UUID) -> None:
        self.created_at = created_at
        self.id = id

    def encode(self) -> str:
        raw = f"{self.created_at.isoformat()}{_SEPARATOR}{self.id}"
        return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")

    @classmethod
    def decode(cls, raw_value: str) -> "KeysetCursor":
        """Rebuild a cursor, or raise ValueError for anything unusable.

        Every malformed shape collapses to one ValueError. The client never builds
        this value itself, so naming which half was wrong helps nobody and
        describes our storage layout to someone probing it.
        """
        if not isinstance(raw_value, str) or not raw_value:
            raise ValueError(INVALID_CURSOR_MESSAGE)
        try:
            decoded = base64.urlsafe_b64decode(raw_value.encode("ascii")).decode("utf-8")
            timestamp, separator, identifier = decoded.partition(_SEPARATOR)
            if not separator:
                raise ValueError(INVALID_CURSOR_MESSAGE)
            return cls(created_at=datetime.fromisoformat(timestamp), id=UUID(identifier))
        except (ValueError, binascii.Error, UnicodeDecodeError) as error:
            raise ValueError(INVALID_CURSOR_MESSAGE) from error

    @classmethod
    def of(cls, entity) -> "KeysetCursor":
        """Anchor on any entity carrying `created_at` and `id`."""
        return cls(created_at=entity.created_at, id=entity.id)
