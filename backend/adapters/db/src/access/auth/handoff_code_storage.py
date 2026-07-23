from datetime import datetime
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from auth.handoff_code import HandoffCode
from model.auth.handoff_code_model import HandoffCodeModel


class SqlAlchemyHandoffCodeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, code: HandoffCode) -> None:
        self._session.add(HandoffCodeModel.from_domain(code))
        await self._session.flush()

    async def redeem(self, value: str, moment: datetime) -> UUID | None:
        """Atomically consume an unexpired code, returning its account id or None.

        A single conditional `DELETE ... WHERE value = :v AND expires_at > :now
        RETURNING account_id`: two concurrent exchanges of one code contend for the
        same row lock, exactly one deletes-and-returns, the other re-checks the WHERE
        after the winner commits, finds the row gone, and returns None. Folding the
        TTL into the WHERE means an expired code is never redeemable even for an
        instant. The caller commits to release the lock and finalize the delete.
        """
        result = await self._session.execute(
            delete(HandoffCodeModel)
            .where(HandoffCodeModel.value == value, HandoffCodeModel.expires_at > moment)
            .returning(HandoffCodeModel.account_id)
        )
        row = result.one_or_none()
        return row.account_id if row is not None else None
