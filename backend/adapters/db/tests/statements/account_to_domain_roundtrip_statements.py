from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from access.auth.account_storage import SqlAlchemyAccountRepository
from auth.account import Account
from statements.arranged import arranged

FAILED_ATTEMPT_COUNT = 3


class AccountToDomainRoundtripStatements:
    """DSL pinning that AccountModel.to_domain() carries failed_attempt_count
    through to the reconstituted Account (scenario 5.4).

    Owns a session factory so the read-back runs on a brand-new session -- the
    domain value comes from a fresh to_domain(), not a stale identity-mapped
    instance the writing session already holds.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self.account_id: UUID | None = None
        self.email: str | None = None
        self.read_back_account: Account | None = None

    @property
    def inserted_account_id(self) -> UUID:
        """The id the insert step generated -- read by every later step."""
        return arranged(self.account_id, "account_id")

    @property
    def inserted_email(self) -> str:
        return arranged(self.email, "email")

    async def insert_account_with_failed_attempts(self) -> None:
        self.account_id = account_id = uuid4()
        # Per-run-unique: uq_accounts_email would make a fixed literal collide
        # (ConflictException) on reruns against the persistent test postgres.
        self.email = email = f"roundtrip-{uuid4()}@example.com"
        account = Account.reconstitute(
            id=account_id,
            email=email,
            password_hash="hashed-password-value",
            created_at=datetime.now(UTC),
            is_verified=True,
        )
        async with self._session_factory() as session:
            repository = SqlAlchemyAccountRepository(session)
            await repository.save(account)
            for _ in range(FAILED_ATTEMPT_COUNT):
                await repository.increment_failed_attempts(account_id)
            await session.commit()

    async def read_back_via_find_by_email(self) -> None:
        async with self._session_factory() as session:
            repository = SqlAlchemyAccountRepository(session)
            self.read_back_account = await repository.find_by_email(self.inserted_email)

    def assert_failed_attempt_count_carried_through(self) -> None:
        assert self.read_back_account is not None, (
            f"expected an Account for {self.email!r}, got None"
        )
        # Load-bearing guard: to_domain() must pass the row's failed_attempt_count
        # into Account.reconstitute. Today it omits it, so the parameter defaults
        # to 0 and every account reads back with count=0 -- making the green-usecase
        # lockout gate production-inert. Exact == FAILED_ATTEMPT_COUNT catches that
        # dropped field (0 == 3 fails).
        assert self.read_back_account.failed_attempt_count == FAILED_ATTEMPT_COUNT, (
            f"expected reconstituted failed_attempt_count={FAILED_ATTEMPT_COUNT}, "
            f"got {self.read_back_account.failed_attempt_count!r}"
        )
