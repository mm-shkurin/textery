from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from access.auth.account_storage import SqlAlchemyAccountRepository
from access.generation.generation_storage import SqlAlchemyGenerationStorage
from auth.account import Account
from generation.generation import Generation
from shared.exceptions import ConflictException, NotFoundException
from statements.arranged import arranged


class GenerationStorageStatements:
    def __init__(self, session: AsyncSession) -> None:
        self._storage = SqlAlchemyGenerationStorage(session)
        self._accounts = SqlAlchemyAccountRepository(session)
        self._session = session
        self._owner_id: UUID | None = None
        self.saved_generation: Generation | None = None
        self.fetched_generation: Generation | None = None
        self.raised_error: Exception | None = None
        self.stale_generations: list[Generation] = []

    # `given_an_account` sets the owner; `save_generation`/`fetch_generation` set
    # the rows. Reading them back through these properties turns "the arrange step
    # ran first" into a checked precondition that names the missing step.
    @property
    def owner_id(self) -> UUID:
        return arranged(self._owner_id, "_owner_id")

    @property
    def saved(self) -> Generation:
        return arranged(self.saved_generation, "saved_generation")

    @property
    def fetched(self) -> Generation:
        return arranged(self.fetched_generation, "fetched_generation")

    async def given_an_account(self) -> UUID:
        # generations.owner_id is a real FK, so a generation needs a real account row.
        account = Account.create(
            id=uuid4(),
            email=f"owner-{uuid4()}@example.com",
            password_hash="hash",
            created_at=datetime.now(UTC),
        )
        await self._accounts.save(account)
        self._owner_id = account.id
        return account.id

    def build_pending_generation(
        self,
        generation_id: UUID | None = None,
        created_at: datetime | None = None,
        owner_id: UUID | None = None,
    ) -> Generation:
        return Generation(
            id=generation_id or uuid4(),
            owner_id=owner_id or self.owner_id,
            status="pending",
            created_at=created_at or datetime.now(UTC),
            topic="Как работает фотосинтез",
            volume_pages=3,
            requirements=None,
            extra_wishes=None,
            document_type="доклад",
            content=None,
        )

    async def save_generation(self, generation: Generation) -> None:
        self.saved_generation = generation
        await self._storage.save(generation)

    async def fetch_generation(self, generation_id: UUID, owner_id: UUID | None = None) -> None:
        self.fetched_generation = await self._storage.get_by_id_and_owner(
            generation_id, owner_id or self.owner_id
        )

    async def update_generation(self, generation: Generation) -> None:
        await self._storage.update(generation)

    async def update_unknown_generation(self) -> None:
        unknown = self.build_pending_generation()
        try:
            await self._storage.update(unknown)
        except NotFoundException as error:
            self.raised_error = error

    async def update_generation_with_stale_version(self, generation: Generation) -> None:
        try:
            await self._storage.update(generation)
        except ConflictException as error:
            self.raised_error = error

    async def fetch_by_saved_id(self) -> None:
        await self.fetch_generation(self.saved.id)

    async def fetch_unknown_generation(self) -> None:
        await self.fetch_generation(uuid4())

    async def fetch_saved_generation_as_another_owner(self) -> None:
        """Read a generation that exists, presenting a different account's id. Proves
        the WHERE clause is what withholds it -- an assertion `fetch_unknown_generation`
        cannot make, since there the row is absent anyway.
        """
        other_owner_id = await self.given_an_account()
        self.fetched_generation = await self._storage.get_by_id_and_owner(
            self.saved.id, other_owner_id
        )

    def assert_fetched_matches_saved(self) -> None:
        assert self.fetched_generation is not None, "expected a Generation, got None"
        actual = (
            self.fetched.id,
            self.fetched.owner_id,
            self.fetched.status,
            self.fetched.topic,
            self.fetched.volume_pages,
            self.fetched.requirements,
            self.fetched.extra_wishes,
            self.fetched.document_type,
            self.fetched.content,
        )
        expected = (
            self.saved.id,
            self.saved.owner_id,
            self.saved.status,
            self.saved.topic,
            self.saved.volume_pages,
            self.saved.requirements,
            self.saved.extra_wishes,
            self.saved.document_type,
            self.saved.content,
        )
        assert actual == expected, f"expected {expected}, got {actual}"

    def assert_fetched_is_none(self) -> None:
        assert self.fetched_generation is None, f"expected None, got {self.fetched_generation}"

    def assert_not_found_error_raised(self) -> None:
        assert isinstance(self.raised_error, NotFoundException), (
            f"expected NotFoundException, got {self.raised_error!r}"
        )

    def assert_conflict_error_raised(self) -> None:
        assert isinstance(self.raised_error, ConflictException), (
            f"expected ConflictException, got {self.raised_error!r}"
        )

    async def save_stale_pending_generation(self) -> Generation:
        generation = self.build_pending_generation(
            created_at=datetime.now(UTC) - timedelta(minutes=30)
        )
        await self._storage.save(generation)
        return generation

    async def save_fresh_pending_generation(self) -> Generation:
        generation = self.build_pending_generation(created_at=datetime.now(UTC))
        await self._storage.save(generation)
        return generation

    async def list_stale_generations(self, older_than_minutes: int = 10) -> None:
        threshold = datetime.now(UTC) - timedelta(minutes=older_than_minutes)
        self.stale_generations = await self._storage.list_stale(threshold)

    def assert_stale_generations_include(self, generation: Generation) -> None:
        stale_ids = {g.id for g in self.stale_generations}
        assert generation.id in stale_ids, f"expected {generation.id} in stale results {stale_ids}"

    def assert_stale_generations_exclude(self, generation: Generation) -> None:
        stale_ids = {g.id for g in self.stale_generations}
        assert generation.id not in stale_ids, (
            f"expected {generation.id} not in stale results {stale_ids}"
        )

    def assert_fetched_status_and_content(
        self, expected_status: str, expected_content: str | None
    ) -> None:
        assert self.fetched.status == expected_status, (
            f"expected status '{expected_status}', got '{self.fetched.status}'"
        )
        assert self.fetched.content == expected_content, (
            f"expected content '{expected_content}', got '{self.fetched.content}'"
        )
