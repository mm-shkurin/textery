from typing import ClassVar

from clients.application.application_client import ApplicationClient
from clients.application.dto.generation.generation_response_dto import GenerationResponseDto
from statements.generation_scope import GenerationScope
from statements.test_data import TestData


class GenerationStatements:
    # Field-level validation errors (missing topic, out-of-range volume_pages, oversized
    # requirements/extra_wishes) are 400 per ProductSpecification/api-specs/generations_create.yaml;
    # 422 is reserved for unsupported document_type or a server-owned field in the body (scenario 1.4/1.5).
    EXPECTED_MISSING_TOPIC_ERROR: ClassVar[dict] = {"detail": "topic is required"}
    EXPECTED_OUT_OF_RANGE_VOLUME_ERROR: ClassVar[dict] = {
        "detail": "volume_pages must be between 1 and 10",
    }

    def __init__(self, client: ApplicationClient):
        self._client = client

    async def given_generation_request_submitted_without_topic(self) -> GenerationResponseDto:
        scope = GenerationScope.builder(topic=None)
        request = scope.to_request_dto()
        return await self._client.create_generation(request, TestData.unique_idempotency_key())

    async def given_generation_request_submitted_with_volume(self, volume_pages: int) -> GenerationResponseDto:
        scope = GenerationScope.builder(volume_pages=volume_pages)
        request = scope.to_request_dto()
        return await self._client.create_generation(request, TestData.unique_idempotency_key())

    def assert_validation_error(self, response: GenerationResponseDto, expected_error: dict) -> None:
        assert response.status_code == 400, (
            f"expected 400 Bad Request (validation error), got {response.status_code}"
        )
        assert response.body == expected_error, (
            f"expected validation error body {expected_error}, got {response.body}"
        )

    def assert_no_generation_created(self, response: GenerationResponseDto) -> None:
        assert response.status_code not in (200, 201), (
            f"expected no generation to be created (2xx would indicate creation), "
            f"got status_code={response.status_code}"
        )
        assert response.body is None or "generation_id" not in response.body, (
            f"expected no generation_id in response, but got body={response.body}"
        )
