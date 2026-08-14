"""DSL for the two claims about `accounts.name` that only a real Postgres can make.

Both steps read back through a SESSION OF THEIR OWN, and that is the whole design
of this file. `create_session_factory` sets `expire_on_commit=False` and
`find_by_id` is `session.get`, which answers off the identity map: a re-read on
the writing session hands back the in-memory object it already holds and is green
against a row that does not exist. A fake repository -- a list of entities --
cannot fail either of these tests for the same reason, which is why neither claim
is asserted at the usecase layer.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from access.auth.account_storage import SqlAlchemyAccountRepository
from auth.account import Account
from model.auth.account_model import AccountModel

FAILED_ATTEMPT_COUNT = 3
ORIGINAL_NAME = "Иван Петров"
RENAMED_TO = "Пётр Иванов"


class AccountNameStorageStatements:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._account_id: UUID | None = None
        self._email: str | None = None
        self._created_at: datetime | None = None
        self._read_back: Account | None = None
        self._row: AccountModel | None = None

    async def given_a_verified_account_with_failed_attempts_and_a_name(self) -> None:
        self._account_id = account_id = uuid4()
        # Per-run-unique: uq_accounts_email makes a fixed literal collide on a
        # rerun against the persistent test database.
        self._email = email = f"profile-{uuid4()}@example.com"
        self._created_at = created_at = datetime.now(UTC)
        account = Account.reconstitute(
            id=account_id,
            email=email,
            password_hash="hashed-password-value",
            created_at=created_at,
            is_verified=True,
        )
        account.rename(ORIGINAL_NAME)
        async with self._session_factory() as session:
            repository = SqlAlchemyAccountRepository(session)
            await repository.save(account)
            for _ in range(FAILED_ATTEMPT_COUNT):
                await repository.increment_failed_attempts(account_id)
            await session.commit()

    async def read_the_account_back_on_a_new_session(self) -> None:
        async with self._session_factory() as session:
            self._read_back = await SqlAlchemyAccountRepository(session).find_by_id(
                self._required_account_id()
            )

    async def rename_the_account(self) -> None:
        async with self._session_factory() as session:
            await SqlAlchemyAccountRepository(session).update_name(
                self._required_account_id(), RENAMED_TO
            )
            await session.commit()

    async def read_the_whole_row_back_on_a_new_session(self) -> None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(AccountModel).where(AccountModel.id == self._required_account_id())
            )
            self._row = result.scalar_one_or_none()

    def assert_the_name_survived_the_round_trip(self) -> None:
        account = self._read_back
        assert account is not None, f"expected account {self._account_id} to be found, got None"
        assert account.name == ORIGINAL_NAME, (
            f"expected the stored name {ORIGINAL_NAME!r}, got {account.name!r}. A name that "
            "is None here means a column list was missed -- save()'s update branch, "
            "AccountModel.from_domain, or AccountModel.to_domain."
        )

    def assert_only_the_name_changed(self) -> None:
        row = self._row
        assert row is not None, f"expected account {self._account_id} to be found, got None"
        actual = (row.name, row.is_verified, row.failed_attempt_count, row.email, row.created_at)
        expected = (
            RENAMED_TO,
            True,
            FAILED_ATTEMPT_COUNT,
            self._email,
            self._created_at,
        )
        # The whole row at once rather than five assertions: a rename that went
        # through save() would rewrite is_verified and email from an entity read
        # before the change, and a lockout counter reset by a stray UPDATE would
        # hand an attacker their attempts back. Comparing the tuple names whichever
        # one moved.
        assert actual == expected, f"expected the row to be exactly {expected!r}, got {actual!r}"

    def _required_account_id(self) -> UUID:
        assert self._account_id is not None, (
            "no account arranged: call given_a_verified_account_... first"
        )
        return self._account_id
