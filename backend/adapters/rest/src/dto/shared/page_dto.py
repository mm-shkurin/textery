from pydantic import BaseModel


class PageDto[ItemT](BaseModel):
    """`{items, next_cursor}` -- the envelope every history list answers with.

    Generic over the item DTO so generations and documents share one shape: a
    client that can page one history can page the other.

    `next_cursor` is null on the last page, which is the client's stop condition.
    There is no `total`: counting the owner's full history per page is the exact
    scan the keyset cursor exists to avoid, and no screen needs the number.
    """

    items: list[ItemT]
    next_cursor: str | None
