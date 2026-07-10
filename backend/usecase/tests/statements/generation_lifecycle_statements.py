from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from fake.generation.fake_generation_provider import FakeGenerationProvider
from fake.generation.fake_generation_storage import FakeGenerationStorage
from generation.generate_document import GenerateDocument
from generation.generation import Generation
from generation.get_generation import GetGeneration


class GenerationLifecycleStatements:
    def __init__(self) -> None:
        self._storage: Optional[FakeGenerationStorage] = None
        self._provider: Optional[FakeGenerationProvider] = None
        self._seeded_generation: Optional[Generation] = None
        self._looked_up_id: Optional[UUID] = None
        self.result: Optional[Generation] = None

    def given_pending_generation(self) -> None:
        self._seed(status="pending", content=None)

    def given_in_progress_generation(self) -> None:
        self._seed(status="in_progress", content=None)

    def given_completed_generation(self, content: str = "Готовый доклад") -> None:
        self._seed(status="completed", content=content)

    def given_no_generation(self) -> None:
        self._storage = FakeGenerationStorage(call_order=[])
        self._looked_up_id = uuid4()

    def _seed(self, status: str, content: Optional[str]) -> None:
        self._storage = FakeGenerationStorage(call_order=[])
        self._seeded_generation = Generation(
            id=uuid4(),
            status=status,
            created_at=datetime.now(timezone.utc),
            topic="Как работает фотосинтез",
            volume_pages=3,
            requirements=None,
            extra_wishes=None,
            document_type="доклад",
            content=content,
        )
        self._storage.seed(self._seeded_generation)
        self._looked_up_id = self._seeded_generation.id

    async def look_up_generation_status(self) -> None:
        usecase = GetGeneration(storage=self._storage)
        self.result = await usecase.execute(self._looked_up_id)

    def assert_status_pending_without_content(self) -> None:
        assert self.result is not None, "expected a Generation to be returned, got None"
        assert self.result.status == "pending", f"expected status 'pending', got '{self.result.status}'"
        assert self.result.content is None, f"expected content None, got '{self.result.content}'"

    def assert_status_completed_with_content(self, expected_content: str) -> None:
        assert self.result is not None, "expected a Generation to be returned, got None"
        assert self.result.status == "completed", f"expected status 'completed', got '{self.result.status}'"
        assert self.result.content == expected_content, (
            f"expected content '{expected_content}', got '{self.result.content}'"
        )

    def assert_generation_not_found(self) -> None:
        assert self.result is None, f"expected None for unknown id, got {self.result}"

    async def process_pending_generation_with_provider_success(self, content: str = "Готовый доклад") -> None:
        self.given_pending_generation()
        self._provider = FakeGenerationProvider()
        self._provider.content_to_return = content
        usecase = GenerateDocument(storage=self._storage, provider=self._provider)
        await usecase.execute(self._seeded_generation.id)

    async def process_pending_generation_with_provider_error(self, error: Exception) -> None:
        self.given_pending_generation()
        self._provider = FakeGenerationProvider()
        self._provider.error_to_raise = error
        usecase = GenerateDocument(storage=self._storage, provider=self._provider)
        await usecase.execute(self._seeded_generation.id)

    def assert_generation_completed_with_content(self, expected_content: str) -> None:
        stored = self._storage.updated_generations[-1]
        assert stored.status == "completed", f"expected status 'completed', got '{stored.status}'"
        assert stored.content == expected_content, (
            f"expected content '{expected_content}', got '{stored.content}'"
        )

    def assert_generation_failed_with_reason(self, expected_reason: str) -> None:
        stored = self._storage.updated_generations[-1]
        assert stored.status == "failed", f"expected status 'failed', got '{stored.status}'"
        assert stored.content == expected_reason, (
            f"expected failure reason '{expected_reason}', got '{stored.content}'"
        )

    def assert_generation_marked_in_progress_before_final_update(self) -> None:
        statuses = [g.status for g in self._storage.updated_generations]
        assert statuses[0] == "in_progress", (
            f"expected first update() to record status 'in_progress', got {statuses}"
        )
