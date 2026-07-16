from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from auth.account import Account
from model.auth.account_model import AccountModel
from shared.exceptions import ConflictException


class SqlAlchemyAccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_email(self, email: str) -> Optional[Account]:
        # Exact match: callers pass Email(...).value, which is already
        # lowercased/NFC-normalized, and the uq_accounts_email constraint is on
        # that same canonical value. A case-insensitive query here would not
        # match how rows are stored.
        result = await self._session.execute(
            select(AccountModel).where(AccountModel.email == email)
        )
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def find_by_id(self, account_id: UUID) -> Optional[Account]:
        model = await self._session.get(AccountModel, account_id)
        return model.to_domain() if model else None

    async def save(self, account: Account) -> None:
        """Insert a new account, or update the one that already exists.

        Insert-only (a bare session.add) is what this used to do, which was
        invisible until /verify went live: registration always inserts, but
        verifying an account saves an Account that already has a row, so add()
        emitted a second INSERT with the same primary key and Postgres rejected it
        with accounts_pkey. The usecase's broad except turned that into a 500. The
        fakes append to a list, so no unit test could see it.
        """
        existing = await self._session.get(AccountModel, account.id)
        if existing is None:
            self._session.add(AccountModel.from_domain(account))
        else:
            existing.email = account.email
            existing.password_hash = account.password_hash
            existing.is_verified = account.is_verified
        try:
            await self._session.flush()
        except IntegrityError as error:
            raise ConflictException(f"account with email {account.email} already exists") from error
