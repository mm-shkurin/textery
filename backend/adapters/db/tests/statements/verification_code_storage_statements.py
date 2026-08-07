import re
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from access.auth.account_storage import SqlAlchemyAccountRepository
from access.auth.verification_code_storage import SqlAlchemyVerificationCodeRepository
from auth.account import Account
from auth.verification_code import VerificationCode
from model.auth.verification_code_model import VerificationCodeModel
from statements.arranged import arranged
from statements.verification_code_storage_assertions import (
    VerificationCodeStorageAssertions,
)

_ASCII_SIX_DIGITS = re.compile(r"^[0-9]{6}$")


def _now() -> datetime:
    return datetime.now(UTC)


class VerificationCodeStorageStatements(VerificationCodeStorageAssertions):
    def __init__(self, session: AsyncSession) -> None:
        self._storage = SqlAlchemyVerificationCodeRepository(session)
        self._account_storage = SqlAlchemyAccountRepository(session)
        self._session = session
        self.saved_code: VerificationCode | None = None
        self.fetched_model: VerificationCodeModel | None = None
        self.reloaded_code: VerificationCode | None = None

    # Set by an arrange/act step; read back through a checked property, so a step
    # called out of order names the arrangement it is missing.
    @property
    def saved(self) -> VerificationCode:
        return arranged(self.saved_code, "saved_code")

    @property
    def fetched(self) -> VerificationCodeModel:
        return arranged(self.fetched_model, "fetched_model")

    @property
    def reloaded(self) -> VerificationCode:
        return arranged(self.reloaded_code, "reloaded_code")

    async def given_saved_account(self) -> Account:
        account = Account.create(
            id=uuid4(),
            email="student@example.com",
            password_hash="hashed-password-value",
            created_at=_now(),
        )
        await self._account_storage.save(account)
        return account

    def build_code_for_account(self, account: Account) -> VerificationCode:
        return VerificationCode.create(
            id=uuid4(),
            account_id=account.id,
            code="007123",
            expires_at=_now() + timedelta(minutes=10),
            created_at=_now(),
        )

    def build_generated_code_for_account(self, account: Account) -> VerificationCode:
        return VerificationCode.generate(
            id=uuid4(),
            account_id=account.id,
            created_at=_now(),
        )

    def build_code_with_created_at(
        self, account: Account, created_at: datetime, code: str = "007123"
    ) -> VerificationCode:
        return VerificationCode.create(
            id=uuid4(),
            account_id=account.id,
            code=code,
            expires_at=created_at + timedelta(minutes=10),
            created_at=created_at,
        )

    async def reload_active_code(self, account_id: UUID) -> None:
        self.reloaded_code = await self._storage.find_active_by_account_id(account_id)

    async def consume_and_resave_reloaded_code(self, consumed_at: datetime) -> None:
        # Drive save()'s UPDATE branch: the reloaded code already has a row, so
        # stamping consumed_at and saving the same id takes the `existing is not
        # None` path (existing.consumed_at = code.consumed_at), not a fresh INSERT.
        code = self.reloaded_code
        assert code is not None, "expected a reloaded code to consume, got None"
        code.consume(consumed_at)
        self.saved_code = code
        await self._storage.save(code)

    async def save_code(self, code: VerificationCode) -> None:
        self.saved_code = code
        await self._storage.save(code)

    async def fetch_saved_code_row(self) -> None:
        stmt = select(VerificationCodeModel).where(VerificationCodeModel.id == self.saved.id)
        result = await self._session.execute(stmt)
        self.fetched_model = result.scalar_one_or_none()
