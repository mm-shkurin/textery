from uuid import UUID

from fake.generation.call_order_recording_fake import CallOrderRecordingFake

CALL_ENQUEUE = "enqueue"


class FakeGenerationQueue(CallOrderRecordingFake):
    def __init__(self, call_order: list) -> None:
        super().__init__(call_order)
        self.enqueued_ids: list[UUID] = []

    async def enqueue(self, generation_id: UUID) -> None:
        self._record(CALL_ENQUEUE, generation_id)
        self.enqueued_ids.append(generation_id)
