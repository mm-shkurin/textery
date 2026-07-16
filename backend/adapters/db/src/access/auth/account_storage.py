from typing import Optional

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

    async def save(self, account: Account) -> None:
        self._session.add(AccountModel.from_domain(account))
        try:
            await self._session.flush()
        except IntegrityError as error:
            raise ConflictException(f"account with email {account.email} already exists") from error
