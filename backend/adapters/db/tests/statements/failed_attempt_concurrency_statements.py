import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from access.auth.account_storage import SqlAlchemyAccountRepository
from auth.account import Account
from model.auth.account_model import AccountModel


class FailedAttemptConcurrencyStatements:
    """DSL for the atomic failed-attempt increment guard (scenario 5.3).

    Owns a session factory so each racing increment runs in its own independent
    AsyncSession/transaction against the same postgres -- a real race, not a
    same-session round-trip.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self.account_id = None
        self.final_failed_attempt_count: int | None = None

    async def insert_verified_account(self) -> None:
        self.account_id = uuid4()
        account = Account.reconstitute(
            id=self.account_id,
            # Per-run-unique: uq_accounts_email would make a fixed literal collide
            # (ConflictException) on reruns against the persistent test postgres.
            email=f"fail-{uuid4()}@example.com",
            password_hash="hashed-password-value",
            created_at=datetime.now(UTC),
            is_verified=True,
        )
        async with self._session_factory() as session:
            await SqlAlchemyAccountRepository(session).save(account)
            await session.commit()

    async def _increment_in_own_session(self) -> None:
        async with self._session_factory() as session:
            await SqlAlchemyAccountRepository(session).increment_failed_attempts(
                self.account_id
            )
            await session.commit()

    async def race_two_increments(self) -> None:
        await asyncio.gather(
            self._increment_in_own_session(),
            self._increment_in_own_session(),
        )

    async def fetch_final_failed_attempt_count(self) -> None:
        async with self._session_factory() as session:
            model = await session.get(AccountModel, self.account_id)
            self.final_failed_attempt_count = (
                model.failed_attempt_count if model else None
            )

    def assert_final_count_is_two(self) -> None:
        # Load-bearing falsification guard: DB-side `SET count = count + 1`
        # serializes on the row lock and both increments land (final == 2). An
        # ORM load-then-save green (both racers read 0, both write 1) yields 1 and
        # fails here -- this assertion is what distinguishes atomic from
        # lost-update, exactly as scenario 5.3 requires.
        assert self.final_failed_attempt_count == 2, (
            f"expected final failed_attempt_count=2 (both atomic increments landed), "
            f"got {self.final_failed_attempt_count!r}"
        )
