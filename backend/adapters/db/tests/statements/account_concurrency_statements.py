import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from access.auth.account_storage import SqlAlchemyAccountRepository
from auth.account import Account
from model.auth.account_model import AccountModel
from statements.arranged import arranged


class AccountConcurrencyStatements:
    """DSL for the exactly-one-transition concurrency guard (scenario 3.6).

    Owns a session factory so each racing call runs in its own independent
    AsyncSession/transaction against the same postgres -- a real race, not a
    same-session round-trip.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self.account_id: UUID | None = None
        self.results: list[bool] = []
        self.race_error: Exception | None = None
        self.final_is_verified: bool | None = None

    @property
    def inserted_account_id(self) -> UUID:
        """The id the insert step generated -- read by every later step."""
        return arranged(self.account_id, "account_id")

    async def insert_pending_account(self) -> None:
        self.account_id = uuid4()
        account = Account.create(
            id=self.account_id,
            # Per-run-unique: uq_accounts_email would make a fixed literal collide
            # (ConflictException) on reruns against the persistent test postgres.
            email=f"race-{uuid4()}@example.com",
            password_hash="hashed-password-value",
            created_at=datetime.now(UTC),
        )
        async with self._session_factory() as session:
            await SqlAlchemyAccountRepository(session).save(account)
            await session.commit()

    async def _transition_in_own_session(self) -> bool:
        async with self._session_factory() as session:
            outcome = await SqlAlchemyAccountRepository(session).transition_to_verified(
                self.inserted_account_id
            )
            await session.commit()
            return outcome

    async def race_two_transitions(self) -> None:
        try:
            self.results = list(
                await asyncio.gather(
                    self._transition_in_own_session(),
                    self._transition_in_own_session(),
                )
            )
        except Exception as error:  # noqa: BLE001 -- assertion (2) pins that none is raised
            self.race_error = error

    async def fetch_final_verified_state(self) -> None:
        async with self._session_factory() as session:
            model = await session.get(AccountModel, self.account_id)
            self.final_is_verified = model.is_verified if model else None

    def assert_exactly_one_transition(self) -> None:
        assert self.race_error is None, f"expected no exception, got {self.race_error!r}"
        assert sorted(self.results) == [False, True], (
            f"expected exactly one True and one False, got {self.results}"
        )

    def assert_final_row_verified(self) -> None:
        assert self.final_is_verified is True, (
            f"expected final row is_verified=True, got {self.final_is_verified!r}"
        )
