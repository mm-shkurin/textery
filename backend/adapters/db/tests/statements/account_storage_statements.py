from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from access.auth.account_storage import SqlAlchemyAccountRepository
from auth.account import Account
from model.auth.account_model import AccountModel


class AccountStorageStatements:
    def __init__(self, session: AsyncSession) -> None:
        self._storage = SqlAlchemyAccountRepository(session)
        self._session = session
        self.saved_account: Optional[Account] = None
        self.fetched_model: Optional[AccountModel] = None

    def build_account(self) -> Account:
        return Account.create(
            id=uuid4(),
            email="student@example.com",
            password_hash="hashed-password-value",
            created_at=datetime.now(timezone.utc),
        )

    async def save_account(self, account: Account) -> None:
        self.saved_account = account
        await self._storage.save(account)

    async def fetch_saved_account_row(self) -> None:
        stmt = select(AccountModel).where(AccountModel.id == self.saved_account.id)
        result = await self._session.execute(stmt)
        self.fetched_model = result.scalar_one_or_none()

    def assert_fetched_matches_saved(self) -> None:
        assert self.fetched_model is not None, "expected an accounts row, got None"
        actual = (
            self.fetched_model.id,
            self.fetched_model.email,
            self.fetched_model.password_hash,
            self.fetched_model.is_verified,
            self.fetched_model.created_at,
        )
        expected = (
            self.saved_account.id,
            self.saved_account.email,
            self.saved_account.password_hash,
            False,
            self.saved_account.created_at,
        )
        assert actual == expected, f"expected {expected}, got {actual}"
