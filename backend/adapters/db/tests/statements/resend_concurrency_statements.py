import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from access.auth.account_storage import SqlAlchemyAccountRepository
from access.auth.verification_code_storage import SqlAlchemyVerificationCodeRepository
from auth.account import Account
from auth.verification_code import VerificationCode


class ResendConcurrencyStatements:
    """DSL for the FOR UPDATE resend-serialization guard (scenario 4.4).

    Owns a session factory so each racing resend critical section runs in its own
    independent AsyncSession/transaction against the same postgres -- a real race,
    not a same-session round-trip. Mirrors AccountConcurrencyStatements.

    The critical section per racer: lock_for_update(account_id) -> read the newest
    code (find_active_by_account_id) -> insert a fresh code -> commit. With the
    account-row lock the two racers SERIALIZE: the loser blocks on the lock until
    the winner commits, then its post-lock read observes the winner's committed
    insert instead of the stale pre-race code. That divergence -- one racer reads
    the seeded code, the other reads a code the first racer inserted -- is what this
    test pins; it can only hold if the reads are serialized by the lock.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self.account_id: UUID | None = None
        self.seeded_code_id: UUID | None = None
        self._now = datetime.now(UTC)
        self.results: list[tuple[UUID, UUID]] = []

    async def insert_eligible_account(self) -> None:
        self.account_id = uuid4()
        account = Account.create(
            id=self.account_id,
            # Per-run-unique: uq_accounts_email would make a fixed literal collide
            # (ConflictException) on reruns against the persistent test postgres.
            email=f"resend-race-{uuid4()}@example.com",
            password_hash="hashed-password-value",
            created_at=self._now,
        )
        self.seeded_code_id = uuid4()
        # 90s in the past: already outside the 60s resend cooldown, so the account
        # is ELIGIBLE -- both racers would pass the usecase cooldown check on the
        # stale read; the db-layer lock is what serializes them.
        eligible_created_at = self._now - timedelta(seconds=90)
        seeded = VerificationCode.create(
            id=self.seeded_code_id,
            account_id=self.account_id,
            code="007123",
            expires_at=eligible_created_at + timedelta(minutes=10),
            created_at=eligible_created_at,
        )
        async with self._session_factory() as session:
            await SqlAlchemyAccountRepository(session).save(account)
            await SqlAlchemyVerificationCodeRepository(session).save(seeded)
            await session.commit()

    async def _resend_in_own_session(self) -> tuple[UUID, UUID]:
        async with self._session_factory() as session:
            # lock_for_update does not exist yet -> AttributeError today (RED). In
            # green it acquires SELECT ... FOR UPDATE on the account row, serializing
            # the two racers on this line.
            await SqlAlchemyAccountRepository(session).lock_for_update(self.account_id)
            code_storage = SqlAlchemyVerificationCodeRepository(session)
            seen = await code_storage.find_active_by_account_id(self.account_id)
            inserted_id = uuid4()
            new_code = VerificationCode.create(
                id=inserted_id,
                account_id=self.account_id,
                code="654321",
                expires_at=self._now + timedelta(minutes=10),
                created_at=self._now,
            )
            await code_storage.save(new_code)
            await session.commit()
            return (seen.id, inserted_id)

    async def race_two_resends(self) -> None:
        # No broad try/except: the whole point of a lock test is to let a real
        # failure (today's missing method; tomorrow a deadlock) surface directly.
        self.results = list(
            await asyncio.gather(
                self._resend_in_own_session(),
                self._resend_in_own_session(),
            )
        )

    def assert_reads_were_serialized(self) -> None:
        seen_ids = [seen for seen, _ in self.results]
        inserted_ids = {inserted for _, inserted in self.results}
        assert seen_ids[0] != seen_ids[1], (
            f"expected the two post-lock reads to diverge under serialization, "
            f"both saw {seen_ids[0]}"
        )
        seeded_reads = [seen for seen in seen_ids if seen == self.seeded_code_id]
        assert len(seeded_reads) == 1, (
            f"expected exactly one racer to read the seeded code {self.seeded_code_id}, "
            f"reads were {seen_ids}"
        )
        loser_read = next(seen for seen in seen_ids if seen != self.seeded_code_id)
        assert loser_read in inserted_ids, (
            f"expected the loser's post-lock read {loser_read} to be a code the winner "
            f"inserted {inserted_ids} -- the serialization signature"
        )
