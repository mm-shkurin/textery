from datetime import UTC, datetime
from uuid import UUID

from fake.generation.fake_generation_queue import CALL_ENQUEUE, FakeGenerationQueue
from fake.generation.fake_generation_storage import CALL_SAVE, FakeGenerationStorage
from scope.generation_request_scope import GenerationRequestScope

from generation.generation import Generation
from generation.request_generation import RequestGeneration
from shared.exceptions import ValidationException


class GenerationStatements:
    EXPECTED_MISSING_TOPIC_MESSAGE = "topic is required"
    EXPECTED_OUT_OF_RANGE_VOLUME_MESSAGE = "volume_pages must be between 1 and 10"

    def __init__(self) -> None:
        self.thrown_exception: Exception | None = None
        self.generation: Generation | None = None
        self._scope: GenerationRequestScope | None = None
        self._call_order: list[tuple[str, object]] | None = None
        self._storage: FakeGenerationStorage | None = None
        self._queue: FakeGenerationQueue | None = None
        self._before_submit: datetime | None = None
        self._after_submit: datetime | None = None

    def attempt_creating_generation_with_topic(self, topic: str | None) -> None:
        scope = GenerationRequestScope.builder(topic=topic)
        self._attempt_creating_generation(scope)

    def assert_missing_topic_error_raised(self) -> None:
        self._assert_validation_error_raised(self.EXPECTED_MISSING_TOPIC_MESSAGE)

    def attempt_creating_generation_with_volume_pages(self, volume_pages: int | None) -> None:
        scope = GenerationRequestScope.builder(volume_pages=volume_pages)
        self._attempt_creating_generation(scope)

    def assert_out_of_range_volume_error_raised(self) -> None:
        self._assert_validation_error_raised(self.EXPECTED_OUT_OF_RANGE_VOLUME_MESSAGE)

    def _attempt_creating_generation(self, scope: GenerationRequestScope) -> None:
        try:
            Generation.create(
                owner_id=scope.owner_id,
                topic=scope.topic,
                volume_pages=scope.volume_pages,
                requirements=scope.requirements,
                extra_wishes=scope.extra_wishes,
                document_type=scope.document_type,
            )
        except Exception as exc:
            self.thrown_exception = exc

    def _assert_validation_error_raised(self, expected_message: str) -> None:
        assert isinstance(self.thrown_exception, ValidationException), (
            f"expected ValidationException to be raised, got "
            f"{type(self.thrown_exception).__name__ if self.thrown_exception else 'no exception'}"
        )
        assert str(self.thrown_exception) == expected_message, (
            f"expected ValidationException message '{expected_message}', "
            f"got '{self.thrown_exception}'"
        )

    async def submit_valid_generation_request(self) -> None:
        self._scope = GenerationRequestScope.builder()
        self._call_order = []
        self._storage = FakeGenerationStorage(self._call_order)
        self._queue = FakeGenerationQueue(self._call_order)
        usecase = RequestGeneration(storage=self._storage, queue=self._queue)
        self._before_submit = datetime.now(UTC)
        self.generation = await usecase.execute(
            owner_id=self._scope.owner_id,
            topic=self._scope.topic,
            volume_pages=self._scope.volume_pages,
            requirements=self._scope.requirements,
            extra_wishes=self._scope.extra_wishes,
            document_type=self._scope.document_type,
        )
        self._after_submit = datetime.now(UTC)

    def assert_generation_accepted_and_pending(self) -> None:
        assert self.generation.status == "pending", (
            f"expected status 'pending', got '{self.generation.status}'"
        )
        # id is generated inside Generation.create() with no API to predict or
        # capture it ahead of time (determinism hierarchy category 4: truly
        # opaque) -- an isinstance check is the strictest assertion available.
        assert isinstance(self.generation.id, UUID), (
            f"expected id to be a UUID, got {type(self.generation.id).__name__}"
        )
        assert self._before_submit <= self.generation.created_at <= self._after_submit, (
            f"expected created_at between {self._before_submit} and {self._after_submit}, "
            f"got {self.generation.created_at}"
        )
        actual_request_fields = (
            self.generation.topic,
            self.generation.volume_pages,
            self.generation.requirements,
            self.generation.extra_wishes,
            self.generation.document_type,
            # Not a request field: the owner comes from the token, never the body.
            # Asserted alongside them so a usecase that dropped it on the floor --
            # or stamped someone else's id -- fails here rather than at the NOT NULL
            # column with a constraint error.
            self.generation.owner_id,
        )
        expected_request_fields = (
            self._scope.topic,
            self._scope.volume_pages,
            self._scope.requirements,
            self._scope.extra_wishes,
            self._scope.document_type,
            self._scope.owner_id,
        )
        assert actual_request_fields == expected_request_fields, (
            f"expected request fields {expected_request_fields}, got {actual_request_fields}"
        )

    def assert_generation_persisted_exactly_once(self) -> None:
        assert self._storage.saved_generations == [self.generation], (
            f"expected save() called exactly once with {self.generation}, "
            f"got {self._storage.saved_generations}"
        )

    def assert_generation_enqueued_exactly_once(self) -> None:
        assert self._queue.enqueued_ids == [self.generation.id], (
            f"expected enqueue() called exactly once with {self.generation.id}, "
            f"got {self._queue.enqueued_ids}"
        )

    def assert_save_happened_before_enqueue(self) -> None:
        expected_order = [
            (CALL_SAVE, self.generation),
            (CALL_ENQUEUE, self.generation.id),
        ]
        assert self._call_order == expected_order, (
            f"expected call order {expected_order}, got {self._call_order}"
        )
