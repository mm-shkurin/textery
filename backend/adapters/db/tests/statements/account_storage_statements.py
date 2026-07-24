from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from access.auth.account_storage import SqlAlchemyAccountRepository
from auth.account import Account
from model.auth.account_model import AccountModel
from shared.exceptions import ConflictException
from statements.account_row_lookup import fetch_account_row_on_new_connection
from statements.arranged import arranged


class AccountStorageStatements:
    def __init__(self, session: AsyncSession) -> None:
        self._storage = SqlAlchemyAccountRepository(session)
        self._session = session
        self.saved_account: Account | None = None
        self.fetched_model: AccountModel | None = None
        self.raised_error: Exception | None = None

    # Set by an arrange/act step; read back through a checked property, so a step
    # called out of order names the arrangement it is missing.
    @property
    def saved(self) -> Account:
        return arranged(self.saved_account, "saved_account")

    @property
    def fetched(self) -> AccountModel:
        return arranged(self.fetched_model, "fetched_model")

    def build_account(self, email: str = "student@example.com") -> Account:
        return Account.create(
            id=uuid4(),
            email=email,
            password_hash="hashed-password-value",
            created_at=datetime.now(UTC),
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
        stmt = select(AccountModel).where(AccountModel.id == self.saved.id)
        result = await self._session.execute(stmt)
        self.fetched_model = result.scalar_one_or_none()

    async def rollback_session(self) -> None:
        await self._session.rollback()

    async def assert_account_absent_on_new_connection(self) -> None:
        row = await fetch_account_row_on_new_connection(self.saved.id)
        assert row is None, f"expected account {self.saved.id} absent after rollback, found a row"

    def assert_fetched_matches_saved(self) -> None:
        assert self.fetched_model is not None, "expected an accounts row, got None"
        actual = (
            self.fetched.id,
            self.fetched.email,
            self.fetched.password_hash,
            self.fetched.is_verified,
            self.fetched.created_at,
        )
        expected = (
            self.saved.id,
            self.saved.email,
            self.saved.password_hash,
            False,
            self.saved.created_at,
        )
        assert actual == expected, f"expected {expected}, got {actual}"
