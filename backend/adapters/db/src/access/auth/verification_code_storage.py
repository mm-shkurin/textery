from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from auth.verification_code import VerificationCode
from model.auth.verification_code_model import VerificationCodeModel


class SqlAlchemyVerificationCodeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, code: VerificationCode) -> None:
        self._session.add(VerificationCodeModel.from_domain(code, created_at=datetime.now(timezone.utc)))
        await self._session.commit()
