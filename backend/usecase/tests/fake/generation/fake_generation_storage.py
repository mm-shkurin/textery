import copy
from datetime import datetime
from uuid import UUID

from fake.generation.call_order_recording_fake import CallOrderRecordingFake
from generation.generation import Generation

CALL_SAVE = "save"
CALL_GET = "get_by_id_and_owner"
CALL_UPDATE = "update"
CALL_LIST_STALE = "list_stale"


class FakeGenerationStorage(CallOrderRecordingFake):
    def __init__(self, call_order: list) -> None:
        super().__init__(call_order)
        self.saved_generations: list[Generation] = []
        self.updated_generations: list[Generation] = []
        self._by_id: dict[UUID, Generation] = {}
        # id -> exception update() should raise once for that row, letting a test
        # stage a lost CAS race without needing two real sessions.
        self.raise_on_update_for: dict[UUID, Exception] = {}

    async def save(self, generation: Generation) -> None:
        self._record(CALL_SAVE, generation)
        self.saved_generations.append(generation)
        self._by_id[generation.id] = generation

    async def get_by_id_and_owner(self, generation_id: UUID, owner_id: UUID) -> Generation | None:
        self._record(CALL_GET, generation_id)
        # The owner predicate is mirrored, not ignored: a fake that returned the row
        # on id alone would keep every ownership test green against a storage that
        # had lost its WHERE clause -- the exact bug this whole change closes.
        generation = self._by_id.get(generation_id)
        if generation is None or generation.owner_id != owner_id:
            return None
        return generation

    async def update(self, generation: Generation) -> None:
        self._record(CALL_UPDATE, generation)
        # Mirrors the real adapter's CAS: it raises when another writer already
        # claimed the row (ConflictException) or the row is gone
        # (NotFoundException). Both are outcomes a caller must handle, so the fake
        # has to be able to produce them.
        error = self.raise_on_update_for.pop(generation.id, None)
        if error is not None:
            raise error
        # generation is mutated in place by the usecase after each update() call
        # (mark_in_progress -> update -> complete/fail -> update); snapshot the
        # status at call time so assertions can see the intermediate state.
        self.updated_generations.append(copy.deepcopy(generation))
        self._by_id[generation.id] = generation

    def seed(self, generation: Generation) -> None:
        self._by_id[generation.id] = generation

    async def list_stale(self, older_than: datetime) -> list[Generation]:
        self._record(CALL_LIST_STALE, older_than)
        return [
            generation
            for generation in self._by_id.values()
            if generation.status in ("pending", "in_progress")
            and generation.created_at < older_than
        ]
