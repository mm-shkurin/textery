from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from access.auth.account_storage import SqlAlchemyAccountRepository
from auth.account import Account
from session import SqlAlchemyUnitOfWork
from statements.account_row_lookup import fetch_account_row_on_new_connection
from statements.arranged import arranged


class SqlAlchemyUnitOfWorkStatements:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._account_storage = SqlAlchemyAccountRepository(session)
        self._unit_of_work = SqlAlchemyUnitOfWork(session)
        self.saved_account: Account | None = None

    @property
    def flushed(self) -> Account:
        """The account `flush_account` put on the session -- read by every assert."""
        return arranged(self.saved_account, "saved_account")

    def build_account(self, email: str = "uow-student@example.com") -> Account:
        return Account.create(
            id=uuid4(),
            email=email,
            password_hash="hashed-password-value",
            created_at=datetime.now(UTC),
        )

    async def flush_account(self, account: Account) -> None:
        self.saved_account = account
        await self._account_storage.save(account)

    async def commit_unit_of_work(self) -> None:
        await self._unit_of_work.commit()

    async def rollback_unit_of_work(self) -> None:
        await self._unit_of_work.rollback()

    async def assert_account_durable_on_new_connection(self) -> None:
        row = await fetch_account_row_on_new_connection(self.flushed.id)
        assert row is not None, (
            f"expected account {self.flushed.id} to be committed via UnitOfWork, found none"
        )
        actual = (row.id, row.email, row.password_hash, row.is_verified, row.created_at)
        expected = (
            self.flushed.id,
            self.flushed.email,
            self.flushed.password_hash,
            False,
            self.flushed.created_at,
        )
        assert actual == expected, f"expected {expected}, got {actual}"

    async def assert_account_absent_on_new_connection(self) -> None:
        row = await fetch_account_row_on_new_connection(self.flushed.id)
        assert row is None, (
            f"expected account {self.flushed.id} to be discarded via "
            f"UnitOfWork.rollback(), found {row}"
        )
