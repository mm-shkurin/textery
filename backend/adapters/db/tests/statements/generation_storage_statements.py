from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from access.generation.generation_storage import SqlAlchemyGenerationStorage
from generation.generation import Generation


class GenerationStorageStatements:
    def __init__(self, session: AsyncSession) -> None:
        self._storage = SqlAlchemyGenerationStorage(session)
        self._session = session
        self.saved_generation: Optional[Generation] = None
        self.fetched_generation: Optional[Generation] = None

    def build_pending_generation(self, generation_id: Optional[UUID] = None) -> Generation:
        return Generation(
            id=generation_id or uuid4(),
            status="pending",
            created_at=datetime.now(timezone.utc),
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

    def assert_fetched_status_and_content(self, expected_status: str, expected_content: Optional[str]) -> None:
        assert self.fetched_generation.status == expected_status, (
            f"expected status '{expected_status}', got '{self.fetched_generation.status}'"
        )
        assert self.fetched_generation.content == expected_content, (
            f"expected content '{expected_content}', got '{self.fetched_generation.content}'"
        )
