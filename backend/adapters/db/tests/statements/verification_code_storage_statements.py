import re
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from access.auth.account_storage import SqlAlchemyAccountRepository
from access.auth.verification_code_storage import SqlAlchemyVerificationCodeRepository
from auth.account import Account
from auth.verification_code import VerificationCode
from model.auth.verification_code_model import VerificationCodeModel

_ASCII_SIX_DIGITS = re.compile(r"^[0-9]{6}$")


class VerificationCodeStorageStatements:
    def __init__(self, session: AsyncSession) -> None:
        self._storage = SqlAlchemyVerificationCodeRepository(session)
        self._account_storage = SqlAlchemyAccountRepository(session)
        self._session = session
        self.saved_code: Optional[VerificationCode] = None
        self.fetched_model: Optional[VerificationCodeModel] = None

    async def given_saved_account(self) -> Account:
        account = Account.create(
            id=uuid4(),
            email="student@example.com",
            password_hash="hashed-password-value",
            created_at=datetime.now(timezone.utc),
        )
        await self._account_storage.save(account)
        return account

    def build_code_for_account(self, account: Account) -> VerificationCode:
        return VerificationCode.create(
            id=uuid4(),
            account_id=account.id,
            code="007123",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )

    def build_generated_code_for_account(self, account: Account) -> VerificationCode:
        return VerificationCode.generate(
            id=uuid4(),
            account_id=account.id,
            created_at=datetime.now(timezone.utc),
        )

    def assert_fetched_code_is_the_generated_str(self) -> None:
        assert self.fetched_model is not None, "expected a verification_codes row, got None"
        # isinstance, not a regex/truthiness check: the failure guarded here is a
        # value object being stored where a `str` belongs, and a VO whose __str__
        # renders six digits would satisfy a pattern check while still breaking
        # matches() and the String(6) column.
        assert isinstance(self.fetched_model.code, str), (
            f"expected the persisted code to be a str, got "
            f"{type(self.fetched_model.code).__name__}"
        )
        assert _ASCII_SIX_DIGITS.fullmatch(self.fetched_model.code) is not None, (
            f"expected the persisted generated code to be exactly six ASCII digits, "
            f"got {self.fetched_model.code!r}"
        )
        assert self.fetched_model.code == self.saved_code.code, (
            f"expected the generated code to survive the model round-trip unchanged, "
            f"got '{self.fetched_model.code}' vs generated '{self.saved_code.code}'"
        )
        assert self.fetched_model.consumed_at is None, (
            f"expected a freshly generated code to persist unconsumed, "
            f"got consumed_at={self.fetched_model.consumed_at}"
        )

    async def save_code(self, code: VerificationCode) -> None:
        self.saved_code = code
        await self._storage.save(code)

    async def fetch_saved_code_row(self) -> None:
        stmt = select(VerificationCodeModel).where(VerificationCodeModel.id == self.saved_code.id)
        result = await self._session.execute(stmt)
        self.fetched_model = result.scalar_one_or_none()

    def assert_fetched_matches_saved(self) -> None:
        assert self.fetched_model is not None, "expected a verification_codes row, got None"
        actual = (
            self.fetched_model.id,
            self.fetched_model.account_id,
            self.fetched_model.code,
            self.fetched_model.expires_at,
            self.fetched_model.consumed_at,
        )
        expected = (
            self.saved_code.id,
            self.saved_code.account_id,
            self.saved_code.code,
            self.saved_code.expires_at,
            None,
        )
        assert actual == expected, f"expected {expected}, got {actual}"
