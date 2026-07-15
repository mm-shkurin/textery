from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from access.auth.account_storage import SqlAlchemyAccountRepository
from auth.account import Account
from model.auth.account_model import AccountModel
from session import create_engine
from shared.exceptions import ConflictException


class AccountStorageStatements:
    def __init__(self, session: AsyncSession) -> None:
        self._storage = SqlAlchemyAccountRepository(session)
        self._session = session
        self.saved_account: Optional[Account] = None
        self.fetched_model: Optional[AccountModel] = None
        self.raised_error: Optional[Exception] = None

    def build_account(self, email: str = "student@example.com") -> Account:
        return Account.create(
            id=uuid4(),
            email=email,
            password_hash="hashed-password-value",
            created_at=datetime.now(timezone.utc),
        )

    async def save_account(self, account: Account) -> None:
        self.saved_account = account
        await self._storage.save(account)

    async def save_account_with_duplicate_email(self, email: str) -> None:
        duplicate = self.build_account(email=email)
        try:
            await self._storage.save(duplicate)
        except ConflictException as error:
            self.raised_error = error

    def assert_conflict_error_raised(self) -> None:
        assert isinstance(self.raised_error, ConflictException), (
            f"expected ConflictException, got {self.raised_error!r}"
        )

    async def fetch_saved_account_row(self) -> None:
        stmt = select(AccountModel).where(AccountModel.id == self.saved_account.id)
        result = await self._session.execute(stmt)
        self.fetched_model = result.scalar_one_or_none()

    async def rollback_session(self) -> None:
        await self._session.rollback()

    async def assert_account_absent_on_new_connection(self) -> None:
        engine = create_engine()
        async with engine.connect() as connection:
            result = await connection.execute(
                select(AccountModel).where(AccountModel.id == self.saved_account.id)
            )
            row = result.first()
        await engine.dispose()
        assert row is None, (
            f"expected account {self.saved_account.id} absent after rollback, found a row"
        )

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
