from typing import Optional

from generation.generation import Generation
from scope.generation_request_scope import GenerationRequestScope
from shared.exceptions import ValidationException


class GenerationStatements:
    EXPECTED_MISSING_TOPIC_MESSAGE = "topic is required"
    EXPECTED_OUT_OF_RANGE_VOLUME_MESSAGE = "volume_pages must be between 1 and 10"

    def __init__(self) -> None:
        self.thrown_exception: Optional[Exception] = None

    def attempt_creating_generation_with_topic(self, topic: Optional[str]) -> None:
        scope = GenerationRequestScope.builder(topic=topic)

        try:
            Generation.create(
                topic=scope.topic,
                volume_pages=scope.volume_pages,
                requirements=scope.requirements,
                extra_wishes=scope.extra_wishes,
                document_type=scope.document_type,
            )
        except Exception as exc:
            self.thrown_exception = exc

    def assert_missing_topic_error_raised(self) -> None:
        self._assert_validation_error_raised(self.EXPECTED_MISSING_TOPIC_MESSAGE)

    def attempt_creating_generation_with_volume_pages(self, volume_pages: Optional[int]) -> None:
        scope = GenerationRequestScope.builder(volume_pages=volume_pages)

        try:
            Generation.create(
                topic=scope.topic,
                volume_pages=scope.volume_pages,
                requirements=scope.requirements,
                extra_wishes=scope.extra_wishes,
                document_type=scope.document_type,
            )
        except Exception as exc:
            self.thrown_exception = exc

    def assert_out_of_range_volume_error_raised(self) -> None:
        self._assert_validation_error_raised(self.EXPECTED_OUT_OF_RANGE_VOLUME_MESSAGE)

    def _assert_validation_error_raised(self, expected_message: str) -> None:
        assert isinstance(self.thrown_exception, ValidationException), (
            f"expected ValidationException to be raised, got "
            f"{type(self.thrown_exception).__name__ if self.thrown_exception else 'no exception'}"
        )
        assert str(self.thrown_exception) == expected_message, (
            f"expected ValidationException message '{expected_message}', "
            f"got '{self.thrown_exception}'"
        )
