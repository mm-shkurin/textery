from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from auth.account import Account
from model.auth.account_model import AccountModel
from shared.exceptions import ConflictException


class SqlAlchemyAccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, account: Account) -> None:
        self._session.add(AccountModel.from_domain(account))
        try:
            await self._session.flush()
        except IntegrityError as error:
            raise ConflictException(f"account with email {account.email} already exists") from error
