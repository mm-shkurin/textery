from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from access.affected_rows import affected_rows
from auth.verification_code import VerificationCode
from model.auth.verification_code_model import VerificationCodeModel


class SqlAlchemyVerificationCodeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_active_by_account_id(self, account_id: UUID) -> VerificationCode | None:
        """Return the most recently issued code for the account, or None.

        Neither expiry nor consumption is filtered here, deliberately. The
        verify-account ADR puts the expiry comparison in the usecase against an
        injected Clock so scenario 3.3's exact-boundary case stays testable with a
        FakeClock, and consumption is left visible so scenario 3.4 can tell a
        replayed code apart from an unknown one. "Active" therefore means "the
        current one", with validity judged by the caller.

        Ordering by created_at desc is also what makes scenario 4.1's resend
        supersede the previous code rather than race it.
        """
        result = await self._session.execute(
            select(VerificationCodeModel)
            .where(VerificationCodeModel.account_id == account_id)
            .order_by(VerificationCodeModel.created_at.desc(), VerificationCodeModel.id.desc())
            .limit(1)
        )
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def transition_to_consumed(self, code_id: UUID, now: datetime) -> bool:
        """Atomically stamp consumed_at for exactly one caller.

        Conditional single-row UPDATE (``WHERE consumed_at IS NULL``): the winning
        racer affects one row (``rowcount == 1`` -> True); every later racer sees the
        row already consumed and affects zero rows (``rowcount == 0`` -> False). Zero
        rows is idempotent success, NOT an error (inverts generation_storage.py's
        zero-row->raise, exactly like account_storage.transition_to_verified): the
        loser resolves to the already-consumed state, no exception. No commit here --
        the caller owns the transaction boundary.
        """
        result = await self._session.execute(
            update(VerificationCodeModel)
            .where(VerificationCodeModel.id == code_id, VerificationCodeModel.consumed_at.is_(None))
            .values(consumed_at=now)
        )
        return affected_rows(result) == 1

    async def save(self, code: VerificationCode) -> None:
        """Insert a newly issued code, or update the one that already exists.

        Same insert-only bug as account_storage: consuming a code saves a
        VerificationCode that already has a row, so add() would emit a duplicate
        INSERT on verification_codes_pkey.

        created_at is written once, at insert, and deliberately not touched on
        update. It is what find_active_by_account_id orders by, so overwriting it
        on consume would let a consumed code jump ahead of a newer one once
        scenario 4.1's resend exists.
        """
        existing = await self._session.get(VerificationCodeModel, code.id)
        if existing is None:
            self._session.add(VerificationCodeModel.from_domain(code))
        else:
            existing.consumed_at = code.consumed_at
        await self._session.flush()
