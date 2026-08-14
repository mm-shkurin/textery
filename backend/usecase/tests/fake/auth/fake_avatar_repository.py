from datetime import datetime
from uuid import UUID

from auth.avatar_repository import StoredAvatar


class FakeAvatarRepository:
    """In-memory `AvatarRepository` double: a store plus the spies its tests need.

    Real semantics where they are observable -- an update replaces whatever was
    there, a clear is unconditional and succeeds on an account that has no image,
    which is the idempotence `DeleteAvatar` promises. The failure levers exist so
    a test can prove the usecase rolls back rather than answering 200 over a write
    that never landed.
    """

    def __init__(self) -> None:
        self.stored: dict[UUID, StoredAvatar] = {}
        self.update_avatar_calls: list[tuple[UUID, bytes, str, datetime]] = []
        self.clear_avatar_calls: list[UUID] = []
        self.find_avatar_calls: list[UUID] = []
        self.raise_on_update: Exception | None = None
        self.raise_on_clear: Exception | None = None
        # Shared with FakeUnitOfWork (both assigned the same list) so a test can
        # pin the ORDER of the write against the commit.
        self.call_log: list[str] | None = None

    async def update_avatar(
        self, account_id: UUID, data: bytes, media_type: str, updated_at: datetime
    ) -> None:
        self.update_avatar_calls.append((account_id, data, media_type, updated_at))
        if self.call_log is not None:
            self.call_log.append("update_avatar")
        if self.raise_on_update is not None:
            raise self.raise_on_update
        self.stored[account_id] = StoredAvatar(
            data=data, media_type=media_type, updated_at=updated_at
        )

    async def clear_avatar(self, account_id: UUID) -> None:
        self.clear_avatar_calls.append(account_id)
        if self.call_log is not None:
            self.call_log.append("clear_avatar")
        if self.raise_on_clear is not None:
            raise self.raise_on_clear
        self.stored.pop(account_id, None)

    async def find_avatar(self, account_id: UUID) -> StoredAvatar | None:
        self.find_avatar_calls.append(account_id)
        return self.stored.get(account_id)
