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

    def assert_reloaded_is_the_newest_code(self, expected: VerificationCode) -> None:
        # The point of this pin: find_active_by_account_id's ORDER BY created_at
        # DESC LIMIT 1 must return the NEWEST of several active rows -- the only db
        # test that saves more than one row for an account. Compare the whole
        # identity (id, code, created_at), not existence: a returned-None or a
        # returned-older (reversed/dropped ORDER BY) must fail here.
        reloaded = self.reloaded_code
        assert reloaded is not None, "expected the newest active code, got None"
        actual = (reloaded.id, reloaded.code, reloaded.created_at)
        wanted = (expected.id, expected.code, expected.created_at)
        assert actual == wanted, (
            f"expected find_active to return the newest code {wanted}, got {actual}"
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

    def assert_created_at_survived_update(
        self, expected_created_at: datetime, expected_consumed_at: datetime
    ) -> None:
        # The write-once invariant: the consume/update path must leave created_at
        # untouched (find_active orders by it -> a rewritten created_at would let a
        # consumed code jump a newer resend). consumed_at is asserted set too, so a
        # no-op save that changed nothing cannot pass this by leaving created_at be.
        reloaded = self.reloaded_code
        assert reloaded is not None, "expected an active code to reload, got None"
        assert reloaded.created_at == expected_created_at, (
            f"expected created_at to survive the consume/update unchanged, "
            f"reloaded created_at {reloaded.created_at!r}, issued {expected_created_at!r}"
        )
        assert reloaded.consumed_at == expected_consumed_at, (
            f"expected the update to have stamped consumed_at, "
            f"got {reloaded.consumed_at!r}, expected {expected_consumed_at!r}"
        )

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
            self.saved.id,
            self.saved.account_id,
            self.saved.code,
            self.saved.expires_at,
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
        assert row.code == self.saved.code, (
            f"expected the generated code to survive the model round-trip unchanged, "
            f"got '{row.code}' vs generated '{self.saved.code}'"
        )
        assert row.consumed_at is None, (
            f"expected a freshly generated code to persist unconsumed, "
            f"got consumed_at={row.consumed_at}"
        )

    async def save_code(self, code: VerificationCode) -> None:
        self.saved_code = code
        await self._storage.save(code)

    async def fetch_saved_code_row(self) -> None:
        stmt = select(VerificationCodeModel).where(VerificationCodeModel.id == self.saved.id)
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
            self.saved.id,
            self.saved.account_id,
            self.saved.code,
            self.saved.expires_at,
            None,
        )
        assert actual == expected, f"expected {expected}, got {actual}"
