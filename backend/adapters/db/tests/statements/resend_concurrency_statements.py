import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from access.auth.account_storage import SqlAlchemyAccountRepository
from access.auth.verification_code_storage import SqlAlchemyVerificationCodeRepository
from auth.account import Account
from auth.verification_code import VerificationCode
from model.auth.verification_code_model import VerificationCodeModel

RESEND_COOLDOWN = timedelta(seconds=60)
_RACE_WINDOW_SECONDS = 0.2


class ResendConcurrencyStatements:
    """DSL for the FOR UPDATE resend single-writer guard (scenario 4.4).

    Owns a session factory so each racing resend critical section runs in its own
    independent AsyncSession/transaction against the same postgres -- a real race,
    not a same-session round-trip. Mirrors AccountConcurrencyStatements.

    Each racer runs the FULL critical section the usecase runs, cooldown gate
    included: lock_for_update(account_id) -> find_active_by_account_id (read the
    newest code) -> ENFORCE the 60s cooldown here in the DSL -> insert a fresh code
    only if eligible -> commit. Simulating the cooldown gate is what lets this
    db-layer test prove the account-row lock makes EXACTLY ONE insert land.

    With the lock the two racers serialize: the winner reads the 90s-old seeded
    code (eligible), inserts, commits; the loser blocks on the lock, then its
    post-lock read observes the winner's fresh code (0s old -> inside cooldown) and
    SKIPS the insert. Net: seed + exactly one -> two rows.

    Without a real lock the two racers both read the stale 90s-old code
    concurrently, both pass the cooldown check, both insert -> three rows. That is
    the double-issue the exactly-one-insert assertion is built to catch.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self.account_id: UUID | None = None
        self.seeded_code_id: UUID | None = None
        self._now = datetime.now(UTC)
        self.results: list[tuple[UUID, UUID | None]] = []
        self.final_code_count: int | None = None
        self.final_active_present: bool | None = None

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
        # is ELIGIBLE -- both racers, on their stale pre-serialization read, would
        # pass the cooldown check; the db-layer lock is what serializes them so only
        # one of them still sees an eligible newest code.
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

    async def _resend_in_own_session(self) -> tuple[UUID, UUID | None]:
        async with self._session_factory() as session:
            # lock_for_update does not exist yet -> AttributeError today (RED). In
            # green it acquires SELECT ... FOR UPDATE on the account row, serializing
            # the two racers on this line.
            await SqlAlchemyAccountRepository(session).lock_for_update(self.account_id)
            code_storage = SqlAlchemyVerificationCodeRepository(session)
            newest = await code_storage.find_active_by_account_id(self.account_id)
            # Widen the read->commit window so the race is deterministic under
            # asyncio's cooperative scheduler. A real SELECT ... FOR UPDATE blocks
            # the second racer at lock_for_update ABOVE -- it never reaches this
            # read until the winner commits and releases the row lock, so it then
            # observes the fresh code and is cooldown-rejected. Without a lock both
            # racers read the stale seeded code inside this window and both insert.
            await asyncio.sleep(_RACE_WINDOW_SECONDS)
            # Cooldown gate, simulated here exactly as the usecase applies it: a
            # newest code younger than 60s means this racer is cooldown-rejected and
            # must NOT issue a new code.
            if newest is not None and self._now - newest.created_at < RESEND_COOLDOWN:
                await session.commit()
                return (newest.id, None)
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
            return (newest.id, inserted_id)

    async def race_two_resends(self) -> None:
        # No broad try/except: the whole point of a lock test is to let a real
        # failure (today's missing method; tomorrow a deadlock) surface directly.
        self.results = list(
            await asyncio.gather(
                self._resend_in_own_session(),
                self._resend_in_own_session(),
            )
        )
        await self._capture_final_state()

    async def _capture_final_state(self) -> None:
        async with self._session_factory() as session:
            count = await session.execute(
                select(func.count())
                .select_from(VerificationCodeModel)
                .where(VerificationCodeModel.account_id == self.account_id)
            )
            self.final_code_count = count.scalar_one()
            active = await SqlAlchemyVerificationCodeRepository(session).find_active_by_account_id(
                self.account_id
            )
            self.final_active_present = active is not None

    def assert_exactly_one_new_code_issued(self) -> None:
        inserts = [inserted for _, inserted in self.results if inserted is not None]
        skips = [seen for seen, inserted in self.results if inserted is None]
        # Load-bearing: the account-row lock must let exactly ONE racer insert. A
        # no-op / ineffective lock double-issues -> two inserts, three total rows.
        assert self.final_code_count == 2, (
            f"expected exactly one new code on top of the seed (2 rows total), got "
            f"{self.final_code_count} -- a second insert means the lock did not "
            f"serialize the resend (double-issue)"
        )
        assert len(inserts) == 1, (
            f"expected exactly one racer to issue a new code, {len(inserts)} did "
            f"(inserted ids {inserts})"
        )
        assert len(skips) == 1, (
            f"expected exactly one racer to be cooldown-rejected, {len(skips)} were"
        )
        # never-zero: an active code is always present through the whole race.
        assert self.final_active_present is True, (
            "expected an active code to always be present, find_active returned None"
        )
        # Serialization signature (secondary): the cooldown-rejected racer's post-lock
        # read is the winner's freshly inserted code -- only possible if the reads
        # were serialized by the lock.
        assert skips[0] == inserts[0], (
            f"expected the cooldown-rejected racer to have read the winner's inserted "
            f"code {inserts[0]}, it read {skips[0]}"
        )
