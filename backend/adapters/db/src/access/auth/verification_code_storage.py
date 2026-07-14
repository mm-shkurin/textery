from sqlalchemy.ext.asyncio import AsyncSession

from auth.verification_code import VerificationCode


class SqlAlchemyVerificationCodeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, code: VerificationCode) -> None:
        raise NotImplementedError
