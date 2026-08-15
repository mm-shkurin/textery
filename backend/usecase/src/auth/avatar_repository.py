from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class StoredAvatar:
    """The image as it came out of storage, ready to be served.

    `media_type` is the one the domain derived from the magic bytes at UPLOAD
    time, carried through storage unchanged. The route serves this value, which
    is what keeps the client's `Content-Type` out of the response it later gets
    back.
    """

    data: bytes
    media_type: str
    updated_at: datetime | None


class AvatarRepository(Protocol):
    """A port of its own, not three more methods on `AccountRepository`.

    Two reasons, and the second is the load-bearing one. It keeps
    `AccountRepository` from growing an image concern; and it makes the ONE place
    that reads `avatar_bytes` a separate, named, greppable thing. `GET /me` is the
    highest-rate query in the product, and the rule that it must never carry the
    image survives only as long as it is obvious which code loads the image and
    which does not. A `find_avatar` sitting between `find_by_email` and
    `update_name` is an invitation to reach for it from a profile read.
    """

    async def update_avatar(
        self, account_id: UUID, data: bytes, media_type: str, updated_at: datetime
    ) -> None: ...

    async def clear_avatar(self, account_id: UUID) -> None: ...

    async def find_avatar(self, account_id: UUID) -> StoredAvatar | None: ...
