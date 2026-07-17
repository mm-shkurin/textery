from datetime import UTC, datetime
from uuid import UUID, uuid4

from fake.generation.fake_generation_provider import FakeGenerationProvider
from fake.generation.fake_generation_storage import FakeGenerationStorage

from generation.generate_document import GENERIC_FAILURE_MESSAGE, GenerateDocument
from generation.generation import Generation
from generation.get_generation import GetGeneration


class GenerationLifecycleStatements:
    def __init__(self) -> None:
        self._storage: FakeGenerationStorage | None = None
        self._provider: FakeGenerationProvider | None = None
        self._seeded_generation: Generation | None = None
        self._looked_up_id: UUID | None = None
        self._looked_up_owner_id: UUID | None = None
        self.result: Generation | None = None

    def given_pending_generation(self) -> None:
        self._seed(status="pending", content=None)

    def given_in_progress_generation(self) -> None:
        self._seed(status="in_progress", content=None)

    def given_completed_generation(self, content: str = "Готовый доклад") -> None:
        self._seed(status="completed", content=content)

    def given_no_generation(self) -> None:
        self._storage = FakeGenerationStorage(call_order=[])
        self._looked_up_id = uuid4()
        self._looked_up_owner_id = uuid4()

    def given_generation_owned_by_someone_else(self) -> None:
        """A generation that exists, seeded under a different owner than the one the
        lookup will present. Distinct from `given_no_generation`: this proves the
        owner predicate is what withholds the row, not the row's absence.
        """
        self._seed(status="completed", content="Чужой доклад")
        self._looked_up_owner_id = uuid4()

    def _seed(self, status: str, content: str | None) -> None:
        self._storage = FakeGenerationStorage(call_order=[])
        self._seeded_generation = Generation(
            id=uuid4(),
            owner_id=uuid4(),
            status=status,
            created_at=datetime.now(UTC),
            topic="Как работает фотосинтез",
            volume_pages=3,
            requirements=None,
            extra_wishes=None,
            document_type="доклад",
            content=content,
        )
        self._storage.seed(self._seeded_generation)
        self._looked_up_id = self._seeded_generation.id
        self._looked_up_owner_id = self._seeded_generation.owner_id

    async def look_up_generation_status(self) -> None:
        usecase = GetGeneration(storage=self._storage)
        self.result = await usecase.execute(self._looked_up_id, self._looked_up_owner_id)

    def assert_status_pending_without_content(self) -> None:
        assert self.result is not None, "expected a Generation to be returned, got None"
        assert self.result.status == "pending", (
            f"expected status 'pending', got '{self.result.status}'"
        )
        assert self.result.content is None, f"expected content None, got '{self.result.content}'"

    def assert_status_completed_with_content(self, expected_content: str) -> None:
        assert self.result is not None, "expected a Generation to be returned, got None"
        assert self.result.status == "completed", (
            f"expected status 'completed', got '{self.result.status}'"
        )
        assert self.result.content == expected_content, (
            f"expected content '{expected_content}', got '{self.result.content}'"
        )

    def assert_generation_not_found(self) -> None:
        assert self.result is None, f"expected None for unknown id, got {self.result}"

    def assert_foreign_generation_withheld(self) -> None:
        """Same assertion as `assert_generation_not_found`, named separately: the
        point under test is that a foreign generation is indistinguishable from an
        absent one, so the two must produce the identical result.
        """
        assert self.result is None, (
            f"expected a foreign generation to be withheld as None, got {self.result}"
        )

    async def process_pending_generation_with_provider_success(
        self, content: str = "Готовый доклад"
    ) -> None:
        self.given_pending_generation()
        self._provider = FakeGenerationProvider()
        self._provider.content_to_return = content
        usecase = GenerateDocument(storage=self._storage, provider=self._provider)
        await usecase.execute(self._seeded_generation.id, self._seeded_generation.owner_id)

    async def process_pending_generation_with_provider_error(self, error: Exception) -> None:
        self.given_pending_generation()
        self._provider = FakeGenerationProvider()
        self._provider.error_to_raise = error
        usecase = GenerateDocument(storage=self._storage, provider=self._provider)
        await usecase.execute(self._seeded_generation.id, self._seeded_generation.owner_id)

    async def process_pending_generation_with_transient_provider_error(
        self, error: Exception, fail_times: int, content: str = "Готовый доклад"
    ) -> None:
        self.given_pending_generation()
        self._provider = FakeGenerationProvider()
        self._provider.error_to_raise = error
        self._provider.fail_times = fail_times
        self._provider.content_to_return = content
        usecase = GenerateDocument(storage=self._storage, provider=self._provider)
        await usecase.execute(self._seeded_generation.id, self._seeded_generation.owner_id)

    async def process_a_generation_that_is_gone(self) -> None:
        """Run GenerateDocument against an id the storage does not hold.

        Reachable without a bug: the sweep re-triggers execution from a list read
        taken earlier, so the row can be deleted between that read and this call.
        """
        self.given_no_generation()
        self._provider = FakeGenerationProvider()
        usecase = GenerateDocument(storage=self._storage, provider=self._provider)
        await usecase.execute(self._looked_up_id, self._looked_up_owner_id)

    def assert_no_generation_was_written(self) -> None:
        assert self._storage.updated_generations == [], (
            "expected no write for a generation that does not exist, got "
            f"{self._storage.updated_generations}"
        )

    def assert_provider_was_not_called(self) -> None:
        assert self._provider.call_count == 0, (
            "expected the provider not to be called for a generation that does not "
            f"exist, got {self._provider.call_count} calls"
        )

    def assert_provider_call_count(self, expected_count: int) -> None:
        assert self._provider.call_count == expected_count, (
            f"expected provider called {expected_count} times, got {self._provider.call_count}"
        )

    def assert_generation_completed_with_content(self, expected_content: str) -> None:
        stored = self._storage.updated_generations[-1]
        assert stored.status == "completed", f"expected status 'completed', got '{stored.status}'"
        assert stored.content == expected_content, (
            f"expected content '{expected_content}', got '{stored.content}'"
        )

    def assert_generation_failed_with_reason(self, expected_reason: str) -> None:
        stored = self._storage.updated_generations[-1]
        assert stored.status == "failed", f"expected status 'failed', got '{stored.status}'"
        assert stored.error_message == expected_reason, (
            f"expected failure reason '{expected_reason}', got '{stored.error_message}'"
        )

    def assert_generation_failed_with_generic_reason(self) -> None:
        self.assert_generation_failed_with_reason(GENERIC_FAILURE_MESSAGE)

    def assert_generation_marked_in_progress_before_final_update(self) -> None:
        statuses = [g.status for g in self._storage.updated_generations]
        assert statuses[0] == "in_progress", (
            f"expected first update() to record status 'in_progress', got {statuses}"
        )
