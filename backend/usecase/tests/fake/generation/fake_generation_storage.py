import copy
from typing import Optional
from uuid import UUID

from fake.generation.call_order_recording_fake import CallOrderRecordingFake
from generation.generation import Generation

CALL_SAVE = "save"
CALL_GET = "get"
CALL_UPDATE = "update"


class FakeGenerationStorage(CallOrderRecordingFake):
    def __init__(self, call_order: list) -> None:
        super().__init__(call_order)
        self.saved_generations: list[Generation] = []
        self.updated_generations: list[Generation] = []
        self._by_id: dict[UUID, Generation] = {}

    async def save(self, generation: Generation) -> None:
        self._record(CALL_SAVE, generation)
        self.saved_generations.append(generation)
        self._by_id[generation.id] = generation

    async def get(self, generation_id: UUID) -> Optional[Generation]:
        self._record(CALL_GET, generation_id)
        return self._by_id.get(generation_id)

    async def update(self, generation: Generation) -> None:
        self._record(CALL_UPDATE, generation)
        # generation is mutated in place by the usecase after each update() call
        # (mark_in_progress -> update -> complete/fail -> update); snapshot the
        # status at call time so assertions can see the intermediate state.
        self.updated_generations.append(copy.deepcopy(generation))
        self._by_id[generation.id] = generation

    def seed(self, generation: Generation) -> None:
        self._by_id[generation.id] = generation
