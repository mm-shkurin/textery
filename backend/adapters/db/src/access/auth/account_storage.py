from sqlalchemy.ext.asyncio import AsyncSession

from auth.account import Account


class SqlAlchemyAccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, account: Account) -> None:
        raise NotImplementedError()
