"""DSL for the avatar column round-trip, against a real Postgres.

Every read-back opens a session OF ITS OWN. With `expire_on_commit=False` and a
`session.get` behind `find_by_id`, a re-read on the writing session is answered
from the identity map and stays green against a row that was never written --
which is precisely the failure the three hand-kept column lists produce.

`avatar_bytes` is `bytea` and mapped `deferred`, so a test that read it off a
loaded AccountModel would ALSO be testing the deferred load rather than the
write. Reads here go through the avatar repository, which names its columns.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from access.auth.account_storage import SqlAlchemyAccountRepository
from access.auth.avatar_storage import SqlAlchemyAvatarRepository
from auth.account import Account
from auth.avatar_repository import StoredAvatar
from model.auth.account_model import AccountModel

FAILED_ATTEMPT_COUNT = 3
ACCOUNT_NAME = "Иван Петров"
MEDIA_TYPE = "image/webp"
# A byte string with a NUL and a high byte in it: `bytea` must carry arbitrary
# binary, and a column or a driver path that treated this as text would mangle
# exactly these bytes.
AVATAR_DATA = b"RIFF\x00\x00\x00\x00WEBP\x00\xff\xfe\x01\x02"


class AvatarStorageStatements:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._account_id: UUID | None = None
        self._email: str | None = None
        self._created_at: datetime | None = None
        self._uploaded_at: datetime | None = None
        self._read_back: StoredAvatar | None = None
        self._row: AccountModel | None = None

    async def given_a_verified_named_account_with_failed_attempts(self) -> None:
        self._account_id = account_id = uuid4()
        self._email = email = f"avatar-{uuid4()}@example.com"
        self._created_at = created_at = datetime.now(UTC)
        account = Account.reconstitute(
            id=account_id,
            email=email,
            password_hash="hashed-password-value",
            created_at=created_at,
            is_verified=True,
        )
        account.rename(ACCOUNT_NAME)
        async with self._session_factory() as session:
            repository = SqlAlchemyAccountRepository(session)
            await repository.save(account)
            for _ in range(FAILED_ATTEMPT_COUNT):
                await repository.increment_failed_attempts(account_id)
            await session.commit()

    async def upload_an_avatar(self) -> None:
        self._uploaded_at = uploaded_at = datetime.now(UTC)
        async with self._session_factory() as session:
            await SqlAlchemyAvatarRepository(session).update_avatar(
                account_id=self._required_account_id(),
                data=AVATAR_DATA,
                media_type=MEDIA_TYPE,
                updated_at=uploaded_at,
            )
            await session.commit()

    async def read_the_avatar_back_on_a_new_session(self) -> None:
        async with self._session_factory() as session:
            self._read_back = await SqlAlchemyAvatarRepository(session).find_avatar(
                self._required_account_id()
            )

    async def read_the_whole_row_back_on_a_new_session(self) -> None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(AccountModel).where(AccountModel.id == self._required_account_id())
            )
            self._row = result.scalar_one_or_none()

    def assert_the_avatar_survived_the_round_trip(self) -> None:
        avatar = self._read_back
        assert avatar is not None, (
            f"expected an avatar for {self._account_id}, got None. A column missing from "
            "update_avatar's value list writes nothing and reports no error."
        )
        actual = (avatar.data, avatar.media_type, avatar.updated_at is not None)
        expected = (AVATAR_DATA, MEDIA_TYPE, True)
        assert actual == expected, (
            f"expected the stored avatar to be exactly {expected!r}, got {actual!r}"
        )

    def assert_nothing_but_the_avatar_changed(self) -> None:
        row = self._row
        assert row is not None, f"expected account {self._account_id} to be found, got None"
        actual = (
            row.name,
            row.email,
            row.is_verified,
            row.failed_attempt_count,
            row.created_at,
        )
        expected = (ACCOUNT_NAME, self._email, True, FAILED_ATTEMPT_COUNT, self._created_at)
        # The identity fields as one tuple: an upload routed through save() would
        # rewrite email and is_verified from a stale snapshot, and an UPDATE that
        # named more columns than it meant to could hand a locked-out attacker
        # their attempts back or wipe the display name the user just set.
        assert actual == expected, f"expected the row to be exactly {expected!r}, got {actual!r}"

    def _required_account_id(self) -> UUID:
        assert self._account_id is not None, (
            "no account arranged: call given_a_verified_named_account_... first"
        )
        return self._account_id
