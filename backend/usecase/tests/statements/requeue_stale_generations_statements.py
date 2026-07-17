from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4

from fake.generation.fake_generation_storage import FakeGenerationStorage
from generation.generation import Generation
from generation.requeue_stale_generations import RequeueStaleGenerations

STALE_AFTER = timedelta(minutes=10)


class RequeueStaleGenerationsStatements:
    def __init__(self) -> None:
        self._storage = FakeGenerationStorage(call_order=[])
        self._now = datetime.now(timezone.utc)
        self.requeued: list[tuple[UUID, UUID]] = []

    def given_stale_pending_generation(self) -> Generation:
        return self._seed(status="pending", age=STALE_AFTER + timedelta(minutes=1))

    def given_stale_in_progress_generation(self) -> Generation:
        return self._seed(status="in_progress", age=STALE_AFTER + timedelta(minutes=1))

    def given_fresh_pending_generation(self) -> Generation:
        return self._seed(status="pending", age=timedelta(seconds=1))

    def given_completed_generation(self) -> Generation:
        return self._seed(status="completed", age=STALE_AFTER + timedelta(minutes=1))

    def _seed(self, status: str, age: timedelta) -> Generation:
        generation = Generation(
            id=uuid4(),
            owner_id=uuid4(),
            status=status,
            created_at=self._now - age,
            topic="Как работает фотосинтез",
            volume_pages=3,
            requirements=None,
            extra_wishes=None,
            document_type="доклад",
            content=None,
        )
        self._storage.seed(generation)
        return generation

    async def sweep_stale_generations(self) -> None:
        usecase = RequeueStaleGenerations(storage=self._storage)
        self.requeued = await usecase.execute(older_than=self._now - STALE_AFTER)

    def assert_requeued(self, *expected: Generation) -> None:
        # The owner is asserted alongside the id, not dropped: the sweep's return
        # value is what the re-trigger uses to locate the row again, and an id
        # paired with the wrong owner would find nothing and silently never run.
        expected_pairs = {(generation.id, generation.owner_id) for generation in expected}
        assert set(self.requeued) == expected_pairs, (
            f"expected requeued (id, owner_id) pairs {expected_pairs}, got {set(self.requeued)}"
        )

    def assert_status_reset_to_pending(self, generation: Generation) -> None:
        stored = self._storage.updated_generations[-1]
        assert stored.id == generation.id, f"expected update() for {generation.id}, got {stored.id}"
        assert stored.status == "pending", f"expected status 'pending', got '{stored.status}'"

    def assert_nothing_requeued(self) -> None:
        assert self.requeued == [], f"expected nothing requeued, got {self.requeued}"
