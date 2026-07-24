from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from access.auth.account_storage import SqlAlchemyAccountRepository
from access.auth.verification_code_storage import SqlAlchemyVerificationCodeRepository
from auth.account import Account
from auth.verification_code import VerificationCode


def _now() -> datetime:
    return datetime.now(UTC)


class ResendOrderingStatements:
    """DSL for two single-session pins backing scenario 4.4's ADR (gaps 1 and 2).

    Tie-break determinism: two active codes with EQUAL created_at but different ids
    -- find_active_by_account_id must return the greater-id row deterministically
    once ORDER BY created_at DESC, id DESC lands.

    Never-zero: a rolled-back second insert leaves the prior committed code as the
    active one -- find_active never returns None because of an aborted resend.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._code_storage = SqlAlchemyVerificationCodeRepository(session)
        self._account_storage = SqlAlchemyAccountRepository(session)
        self.expected_max_id: UUID | None = None
        self.committed_code_id: UUID | None = None
        self.reloaded: VerificationCode | None = None

    async def _save_account(self) -> Account:
        account = Account.create(
            id=uuid4(),
            email=f"resend-order-{uuid4()}@example.com",
            password_hash="hashed-password-value",
            created_at=_now(),
        )
        await self._account_storage.save(account)
        return account

    def _build_code(
        self, account_id: UUID, code_id: UUID, created_at: datetime, code: str = "007123"
    ) -> VerificationCode:
        return VerificationCode.create(
            id=code_id,
            account_id=account_id,
            code=code,
            expires_at=created_at + timedelta(minutes=10),
            created_at=created_at,
        )

    async def save_two_codes_with_equal_created_at(self) -> None:
        account = await self._save_account()
        # Two distinct ids; postgres uuid ORDER BY is byte-wise big-endian, matching
        # Python's UUID comparison, so max() here is exactly the row `id DESC` picks.
        id_a, id_b = uuid4(), uuid4()
        self.expected_max_id = max(id_a, id_b)
        tied_created_at = _now()
        await self._code_storage.save(self._build_code(account.id, id_a, tied_created_at))
        await self._code_storage.save(self._build_code(account.id, id_b, tied_created_at))
        await self._session.commit()
        self.reloaded = await self._code_storage.find_active_by_account_id(account.id)

    def assert_returns_greater_id_code(self) -> None:
        assert self.reloaded is not None, "expected an active code on the tie, got None"
        assert self.reloaded.id == self.expected_max_id, (
            f"expected the tie to deterministically return the greater-id code "
            f"{self.expected_max_id}, got {self.reloaded.id}"
        )

    async def save_committed_code_then_rollback_second_insert(self) -> None:
        account = await self._save_account()
        self.committed_code_id = uuid4()
        code_a = self._build_code(account.id, self.committed_code_id, _now(), code="111111")
        await self._code_storage.save(code_a)
        await self._session.commit()
        # Drive a second insert and abort it WITHOUT committing: rollback discards
        # code B's INSERT while committed code A survives.
        code_b = self._build_code(account.id, uuid4(), _now(), code="222222")
        await self._code_storage.save(code_b)
        await self._session.rollback()
        self.reloaded = await self._code_storage.find_active_by_account_id(account.id)

    def assert_active_is_committed_code_never_none(self) -> None:
        assert self.reloaded is not None, (
            "expected the committed code to remain active after the rolled-back insert, got None"
        )
        assert self.reloaded.id == self.committed_code_id, (
            f"expected find_active to still return the committed code "
            f"{self.committed_code_id}, got {self.reloaded.id}"
        )
