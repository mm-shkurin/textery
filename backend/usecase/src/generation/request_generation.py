from uuid import UUID

from analytics.analytics_recorder import AnalyticsRecorder, NullAnalyticsRecorder, occurrence_of
from analytics.event_names import GENERATION_STARTED
from analytics.generation_visitor_log import GenerationVisitorLog, NullGenerationVisitorLog
from generation.generation import Generation
from generation.generation_queue import GenerationQueue
from generation.generation_storage import GenerationStorage


class RequestGeneration:
    """Orchestrates submission of a new generation request.

    Scenario 1.1 scope: delegate field validation to the domain factory,
    letting ValidationException propagate uncaught.

    Scenario 2.1 scope: per the persist-and-enqueue architecture decision,
    a valid request is persisted via GenerationStorage.save() and then
    handed off to GenerationQueue.enqueue() before returning.
    """

    def __init__(
        self,
        storage: GenerationStorage,
        queue: GenerationQueue,
        analytics_recorder: AnalyticsRecorder | None = None,
        generation_visitor_log: GenerationVisitorLog | None = None,
    ) -> None:
        self._storage = storage
        self._queue = queue
        # Both null by default and both fail-open at use. A generation that was
        # persisted and enqueued must be returned to the caller whatever
        # analytics does -- the request is the product, the event is a note
        # about it.
        self._analytics_recorder = analytics_recorder or NullAnalyticsRecorder()
        self._generation_visitor_log = generation_visitor_log or NullGenerationVisitorLog()

    async def execute(
        self,
        owner_id: UUID,
        topic: str | None,
        volume_pages: int | None,
        requirements: str | None,
        extra_wishes: str | None,
        document_type: str,
        text_style: str | None = None,
        visitor_id: UUID | None = None,
    ) -> Generation:
        generation = Generation.create(
            owner_id=owner_id,
            topic=topic,
            volume_pages=volume_pages,
            requirements=requirements,
            extra_wishes=extra_wishes,
            document_type=document_type,
            text_style=text_style,
        )
        await self._storage.save(generation)
        await self._queue.enqueue(generation.id)
        await self._record_start(generation, visitor_id)
        return generation

    async def _record_start(self, generation: Generation, visitor_id: UUID | None) -> None:
        """Record the start, and remember the browser that asked for it.

        Remembering is the half that matters later: the completion happens
        minutes afterwards in a background task, possibly on another instance,
        where the requesting browser is otherwise unknowable (§9.1, §9.2). It is
        written to a table of its own rather than onto the generation, so a
        product entity grows no field for a marketing join.

        The occurrence key is derived from the generation, so a retry of the same
        HTTP request records ONE start (§9.5) -- a new generation gets a new id
        and therefore a new key, which is exactly the distinction §9.5 draws.
        """
        await self._generation_visitor_log.remember(generation.id, visitor_id)
        await self._analytics_recorder.record(
            event_name=GENERATION_STARTED,
            visitor_id=visitor_id,
            user_id=generation.owner_id,
            payload={"document_type": generation.document_type},
            occurrence_key=occurrence_of(GENERATION_STARTED, generation.id),
        )
