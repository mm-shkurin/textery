from fake.generation.call_order_recording_fake import CallOrderRecordingFake
from generation.generation import Generation

CALL_SAVE = "save"


class FakeGenerationStorage(CallOrderRecordingFake):
    def __init__(self, call_order: list) -> None:
        super().__init__(call_order)
        self.saved_generations: list[Generation] = []

    async def save(self, generation: Generation) -> None:
        self._record(CALL_SAVE, generation)
        self.saved_generations.append(generation)
