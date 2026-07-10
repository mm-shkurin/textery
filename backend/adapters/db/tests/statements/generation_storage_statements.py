from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from access.generation.generation_storage import SqlAlchemyGenerationStorage
from generation.generation import Generation
from shared.exceptions import ConflictException, NotFoundException


class GenerationStorageStatements:
    def __init__(self, session: AsyncSession) -> None:
        self._storage = SqlAlchemyGenerationStorage(session)
        self._session = session
        self.saved_generation: Optional[Generation] = None
        self.fetched_generation: Optional[Generation] = None
        self.raised_error: Optional[Exception] = None
        self.stale_generations: list[Generation] = []

    def build_pending_generation(
        self, generation_id: Optional[UUID] = None, created_at: Optional[datetime] = None
    ) -> Generation:
        return Generation(
            id=generation_id or uuid4(),
            status="pending",
            created_at=created_at or datetime.now(timezone.utc),
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

    async def fetch_generation(self, generation_id: UUID) -> None:
        self.fetched_generation = await self._storage.get(generation_id)

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
        await self.fetch_generation(self.saved_generation.id)

    async def fetch_unknown_generation(self) -> None:
        await self.fetch_generation(uuid4())

    def assert_fetched_matches_saved(self) -> None:
        assert self.fetched_generation is not None, "expected a Generation, got None"
        actual = (
            self.fetched_generation.id,
            self.fetched_generation.status,
            self.fetched_generation.topic,
            self.fetched_generation.volume_pages,
            self.fetched_generation.requirements,
            self.fetched_generation.extra_wishes,
            self.fetched_generation.document_type,
            self.fetched_generation.content,
        )
        expected = (
            self.saved_generation.id,
            self.saved_generation.status,
            self.saved_generation.topic,
            self.saved_generation.volume_pages,
            self.saved_generation.requirements,
            self.saved_generation.extra_wishes,
            self.saved_generation.document_type,
            self.saved_generation.content,
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
        generation = self.build_pending_generation(created_at=datetime.now(timezone.utc) - timedelta(minutes=30))
        await self._storage.save(generation)
        return generation

    async def save_fresh_pending_generation(self) -> Generation:
        generation = self.build_pending_generation(created_at=datetime.now(timezone.utc))
        await self._storage.save(generation)
        return generation

    async def list_stale_generations(self, older_than_minutes: int = 10) -> None:
        threshold = datetime.now(timezone.utc) - timedelta(minutes=older_than_minutes)
        self.stale_generations = await self._storage.list_stale(threshold)

    def assert_stale_generations_include(self, generation: Generation) -> None:
        stale_ids = {g.id for g in self.stale_generations}
        assert generation.id in stale_ids, f"expected {generation.id} in stale results {stale_ids}"

    def assert_stale_generations_exclude(self, generation: Generation) -> None:
        stale_ids = {g.id for g in self.stale_generations}
        assert generation.id not in stale_ids, f"expected {generation.id} not in stale results {stale_ids}"

    def assert_fetched_status_and_content(self, expected_status: str, expected_content: Optional[str]) -> None:
        assert self.fetched_generation.status == expected_status, (
            f"expected status '{expected_status}', got '{self.fetched_generation.status}'"
        )
        assert self.fetched_generation.content == expected_content, (
            f"expected content '{expected_content}', got '{self.fetched_generation.content}'"
        )
