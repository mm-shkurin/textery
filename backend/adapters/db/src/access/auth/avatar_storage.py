from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from auth.avatar_repository import StoredAvatar
from model.auth.account_model import AccountModel


class SqlAlchemyAvatarRepository:
    """The only code in the project that reads or writes `accounts.avatar_bytes`.

    Deliberately its own class rather than three more methods on
    `SqlAlchemyAccountRepository`: `GET /me` runs on every authenticated page view
    and must never carry the image, and that rule holds only while it is obvious
    which repository loads images. Every statement below names its columns
    explicitly, so nothing here can accidentally pull a whole row.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def update_avatar(
        self, account_id: UUID, data: bytes, media_type: str, updated_at: datetime
    ) -> None:
        """Store the bytes, their proven media type, and the instant -- in one statement.

        One UPDATE for all three columns, so there is no window in which bytes
        exist without the media type that says how to serve them. No read first:
        an upload overwrites whatever was there, and the previous image is of no
        interest.

        `media_type` is what the domain derived from the magic bytes, never the
        client's `Content-Type`. It is the value `GET .../avatar` answers with, so
        storing the client's header here would let an uploader choose the type its
        own bytes are served under.

        No commit here -- the caller owns the transaction boundary.
        """
        await self._session.execute(
            update(AccountModel)
            .where(AccountModel.id == account_id)
            .values(
                avatar_bytes=data,
                avatar_media_type=media_type,
                avatar_updated_at=updated_at,
            )
        )

    async def clear_avatar(self, account_id: UUID) -> None:
        """NULL all three columns, whether or not there was an avatar.

        No `WHERE avatar_bytes IS NOT NULL`: DELETE is idempotent by contract, so
        "already absent" is success and zero rows changed is not an error. A guard
        that made the statement conditional would turn the second call into the
        404 the contract explicitly rules out.
        """
        await self._session.execute(
            update(AccountModel)
            .where(AccountModel.id == account_id)
            .values(avatar_bytes=None, avatar_media_type=None, avatar_updated_at=None)
        )

    async def find_avatar(self, account_id: UUID) -> StoredAvatar | None:
        """The stored image, or None when there is none.

        A three-column SELECT rather than loading the AccountModel and reading its
        attributes: `avatar_bytes` and `avatar_media_type` are mapped `deferred`,
        so going through the entity would cost one query for the row and a second
        for the image.

        `None` covers "no such account" and "no avatar" alike -- the route answers
        404 for both, and the auth dependency has already proven the account
        exists, so the cases cannot be distinguished here anyway.
        """
        result = await self._session.execute(
            select(
                AccountModel.avatar_bytes,
                AccountModel.avatar_media_type,
                AccountModel.avatar_updated_at,
            ).where(AccountModel.id == account_id)
        )
        row = result.first()
        # Both columns are checked, not just the bytes: they are written and
        # cleared together, so a row with one and not the other is corrupt rather
        # than empty, and serving bytes with no media type would mean guessing one.
        if row is None or row.avatar_bytes is None or row.avatar_media_type is None:
            return None
        return StoredAvatar(
            data=row.avatar_bytes,
            media_type=row.avatar_media_type,
            updated_at=row.avatar_updated_at,
        )
