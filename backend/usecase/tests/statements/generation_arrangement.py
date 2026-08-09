"""The generation a lifecycle test is arranged against, and the state it leaves behind.

Split out of `generation_lifecycle_statements` when that file outgrew the
file-size limit. The seam is the one the class already had: everything here is
*arrangement* -- the seeded row, the fakes, the ids the act will present, and the
recorded backoff -- while the acts that run a usecase and the assertions that read
its result stay with the Statements class that inherits this.

Extracted as a base class rather than a collaborator so no test or fixture has to
change hands, which is the same shape `revision_guard_base` and `ai_edit_guard_base`
already use for this package.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fake.generation.fake_generation_provider import FakeGenerationProvider
from fake.generation.fake_generation_storage import FakeGenerationStorage
from generation.generation import Generation
from statements.arranged import arranged


class GenerationArrangement:
    """One seeded generation, the fakes it lives in, and the ids the act presents."""

    def __init__(self) -> None:
        self._storage: FakeGenerationStorage | None = None
        self._provider: FakeGenerationProvider | None = None
        self._seeded_generation: Generation | None = None
        self._looked_up_id: UUID | None = None
        self._looked_up_owner_id: UUID | None = None
        self.result: Generation | None = None
        # Retry backoff is real time; record what was asked for instead of
        # sleeping it, so the retry tests stay instant and can assert the wait.
        self.slept_for: list[float] = []

    # Each `given_*` step sets the fields it needs; every act and assert step
    # reads them back. The properties make that ordering a checked precondition
    # rather than an assumption repeated at two dozen call sites.
    @property
    def storage(self) -> FakeGenerationStorage:
        return arranged(self._storage, "_storage")

    @property
    def provider(self) -> FakeGenerationProvider:
        return arranged(self._provider, "_provider")

    @property
    def seeded_generation(self) -> Generation:
        return arranged(self._seeded_generation, "_seeded_generation")

    @property
    def looked_up_id(self) -> UUID:
        return arranged(self._looked_up_id, "_looked_up_id")

    @property
    def looked_up_owner_id(self) -> UUID:
        return arranged(self._looked_up_owner_id, "_looked_up_owner_id")

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

    async def _record_sleep(self, seconds: float) -> None:
        self.slept_for.append(seconds)
