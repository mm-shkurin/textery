import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from access.auth.account_storage import SqlAlchemyAccountRepository
from access.auth.verification_code_storage import SqlAlchemyVerificationCodeRepository
from auth.account import Account
from auth.verification_code import VerificationCode
from model.auth.verification_code_model import VerificationCodeModel
from statements.arranged import arranged


class VerificationCodeConcurrencyStatements:
    """DSL for the exactly-one-consume concurrency guard (scenario 3.6, second guard).

    Owns a session factory so each racing call to transition_to_consumed runs in
    its own independent AsyncSession/transaction against the same postgres -- a
    real race, not a same-session round-trip. Mirrors AccountConcurrencyStatements.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self.code_id: UUID | None = None
        self.results: list[bool] = []
        self.race_error: Exception | None = None
        self.final_consumed_at: datetime | None = None
        self._now = datetime.now(UTC)

    @property
    def inserted_code_id(self) -> UUID:
        """The code id the insert step generated -- read by every racer."""
        return arranged(self.code_id, "code_id")

    async def insert_pending_account_with_unconsumed_code(self) -> None:
        account_id = uuid4()
        account = Account.create(
            id=account_id,
            # Per-run-unique: uq_accounts_email would make a fixed literal collide
            # (ConflictException) on reruns against the persistent test postgres.
            email=f"consume-race-{uuid4()}@example.com",
            password_hash="hashed-password-value",
            created_at=self._now,
        )
        self.code_id = code_id = uuid4()
        code = VerificationCode.create(
            id=code_id,
            account_id=account_id,
            code="007123",
            expires_at=self._now + timedelta(minutes=10),
            created_at=self._now,
        )
        async with self._session_factory() as session:
            await SqlAlchemyAccountRepository(session).save(account)
            await SqlAlchemyVerificationCodeRepository(session).save(code)
            await session.commit()

    async def _consume_in_own_session(self) -> bool:
        async with self._session_factory() as session:
            outcome = await SqlAlchemyVerificationCodeRepository(session).transition_to_consumed(
                self.inserted_code_id, self._now
            )
            await session.commit()
            return outcome

    async def race_two_consumes(self) -> None:
        try:
            self.results = list(
                await asyncio.gather(
                    self._consume_in_own_session(),
                    self._consume_in_own_session(),
                )
            )
        except Exception as error:  # noqa: BLE001 -- assertion (2) pins that none is raised
            self.race_error = error

    async def fetch_final_consumed_state(self) -> None:
        async with self._session_factory() as session:
            model = await session.get(VerificationCodeModel, self.code_id)
            self.final_consumed_at = model.consumed_at if model else None

    def assert_exactly_one_consume(self) -> None:
        assert self.race_error is None, f"expected no exception, got {self.race_error!r}"
        assert sorted(self.results) == [False, True], (
            f"expected exactly one True and one False, got {self.results}"
        )

    def assert_final_row_consumed(self) -> None:
        # Strict: the winning transition stamped the exact self._now we passed in,
        # so the persisted consumed_at must equal it -- not merely "be set". Both
        # are tz-aware UTC datetimes, so == compares the same instant precisely.
        assert self.final_consumed_at == self._now, (
            f"expected final row consumed_at=={self._now!r}, got {self.final_consumed_at!r}"
        )
