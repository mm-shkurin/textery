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

_ASCII_SIX_DIGITS = re.compile(r"^[0-9]{6}$")


def _now() -> datetime:
    return datetime.now(UTC)


class VerificationCodeStorageStatements:
    def __init__(self, session: AsyncSession) -> None:
        self._storage = SqlAlchemyVerificationCodeRepository(session)
        self._account_storage = SqlAlchemyAccountRepository(session)
        self._session = session
        self.saved_code: VerificationCode | None = None
        self.fetched_model: VerificationCodeModel | None = None
        self.reloaded_code: VerificationCode | None = None

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
        self, account: Account, created_at: datetime
    ) -> VerificationCode:
        return VerificationCode.create(
            id=uuid4(),
            account_id=account.id,
            code="007123",
            expires_at=created_at + timedelta(minutes=10),
            created_at=created_at,
        )

    async def reload_active_code(self, account_id: UUID) -> None:
        self.reloaded_code = await self._storage.find_active_by_account_id(account_id)

    def assert_reloaded_code_matches_saved(self, expected_created_at: datetime) -> None:
        # Assert the WHOLE object rebuilt by find_active_by_account_id -> to_domain,
        # not just created_at: this is the only test that exercises the to_domain
        # reload path (TestSave reads the raw model row instead), so every field
        # that path reconstitutes is pinned here. created_at is checked against the
        # known past instant -- the behavior under test; the rest against the code
        # that was saved.
        reloaded = self.reloaded_code
        assert reloaded is not None, "expected an active code to reload, got None"
        assert reloaded.created_at == expected_created_at, (
            f"expected the domain-issued created_at to survive the db round-trip, "
            f"reloaded created_at {reloaded.created_at!r}, issued {expected_created_at!r}"
        )
        actual = (
            reloaded.id,
            reloaded.account_id,
            reloaded.code,
            reloaded.expires_at,
            reloaded.consumed_at,
        )
        expected = (
            self.saved_code.id,
            self.saved_code.account_id,
            self.saved_code.code,
            self.saved_code.expires_at,
            None,
        )
        assert actual == expected, (
            f"expected the reloaded code to round-trip unchanged, expected {expected}, got {actual}"
        )

    def _require_fetched_row(self) -> VerificationCodeModel:
        assert self.fetched_model is not None, "expected a verification_codes row, got None"
        return self.fetched_model

    def assert_fetched_code_is_the_generated_str(self) -> None:
        row = self._require_fetched_row()
        # isinstance, not a regex/truthiness check: the failure guarded here is a
        # value object being stored where a `str` belongs, and a VO whose __str__
        # renders six digits would satisfy a pattern check while still breaking
        # matches() and the String(6) column.
        assert isinstance(row.code, str), (
            f"expected the persisted code to be a str, got {type(row.code).__name__}"
        )
        assert _ASCII_SIX_DIGITS.fullmatch(row.code) is not None, (
            f"expected the persisted generated code to be exactly six ASCII digits, "
            f"got {row.code!r}"
        )
        assert row.code == self.saved_code.code, (
            f"expected the generated code to survive the model round-trip unchanged, "
            f"got '{row.code}' vs generated '{self.saved_code.code}'"
        )
        assert row.consumed_at is None, (
            f"expected a freshly generated code to persist unconsumed, "
            f"got consumed_at={row.consumed_at}"
        )

    async def save_code(self, code: VerificationCode) -> None:
        self.saved_code = code
        await self._storage.save(code)

    async def fetch_saved_code_row(self) -> None:
        stmt = select(VerificationCodeModel).where(VerificationCodeModel.id == self.saved_code.id)
        result = await self._session.execute(stmt)
        self.fetched_model = result.scalar_one_or_none()

    def assert_fetched_matches_saved(self) -> None:
        row = self._require_fetched_row()
        actual = (
            row.id,
            row.account_id,
            row.code,
            row.expires_at,
            row.consumed_at,
        )
        expected = (
            self.saved_code.id,
            self.saved_code.account_id,
            self.saved_code.code,
            self.saved_code.expires_at,
            None,
        )
        assert actual == expected, f"expected {expected}, got {actual}"
