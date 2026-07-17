from typing import Generic, TypeVar

from pydantic import BaseModel

_Item = TypeVar("_Item")


class PageDto(BaseModel, Generic[_Item]):
    """`{items, next_cursor}` -- the envelope every history list answers with.

    Generic over the item DTO so generations and documents share one shape: a
    client that can page one history can page the other.

    `next_cursor` is null on the last page, which is the client's stop condition.
    There is no `total`: counting the owner's full history per page is the exact
    scan the keyset cursor exists to avoid, and no screen needs the number.
    """

    items: list[_Item]
    next_cursor: str | None
