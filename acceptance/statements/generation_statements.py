import asyncio
from datetime import datetime, timedelta, timezone
from typing import ClassVar
from uuid import UUID

from clients.application.application_client import ApplicationClient
from clients.application.dto.generation.generation_response_dto import GenerationResponseDto
from statements.generation_scope import GenerationScope
from statements.test_data import TestData

CREATED_AT_MAX_AGE = timedelta(minutes=1)
GENERATION_POLL_ATTEMPTS = 10
GENERATION_POLL_INTERVAL_SECONDS = 0.5
TERMINAL_STATUSES = ("completed", "failed")


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

    async def given_valid_generation_request_submitted(self) -> GenerationResponseDto:
        scope = GenerationScope.builder()
        request = scope.to_request_dto()
        return await self._client.create_generation(request, TestData.unique_idempotency_key())

    async def await_generation_completed(self, create_response: GenerationResponseDto) -> GenerationResponseDto:
        assert create_response.body is not None, "cannot poll: create response had no body"
        generation_id = create_response.body["generation_id"]
        last_response = None
        for _ in range(GENERATION_POLL_ATTEMPTS):
            last_response = await self._client.get_generation(generation_id)
            self._assert_get_generation_ok(last_response)
            status = (last_response.body or {}).get("status")
            if status in TERMINAL_STATUSES:
                return last_response
            await asyncio.sleep(GENERATION_POLL_INTERVAL_SECONDS)
        raise AssertionError(
            f"generation {generation_id} did not reach a terminal status within "
            f"{GENERATION_POLL_ATTEMPTS} polls; last body={last_response.body if last_response else None}"
        )

    def _assert_get_generation_ok(self, response: GenerationResponseDto) -> None:
        assert response.status_code == 200, (
            f"expected 200 OK from GET generation, got status_code={response.status_code}, "
            f"body={response.body}"
        )

    def assert_generation_completed_with_content(
        self, completed_response: GenerationResponseDto, create_response: GenerationResponseDto
    ) -> None:
        self._assert_get_generation_ok(completed_response)
        body = completed_response.body
        assert body is not None, "expected a response body, got None"
        assert body.get("status") == "completed", f"expected status 'completed', got body={body}"

        created = create_response.body
        # created_at is stamped at creation and immutable, so the completed GET must echo the
        # exact value returned by the create (201) response — capturable from setup, assert equal.
        for field in ("generation_id", "topic", "document_type", "volume_pages", "created_at"):
            assert body.get(field) == created.get(field), (
                f"expected {field} to match the created generation ({created.get(field)!r}), "
                f"got {body.get(field)!r}"
            )

        assert body.get("error_message") is None, (
            f"expected no error_message on a successfully completed generation, "
            f"got {body.get('error_message')!r}"
        )

        content = body.get("content")
        assert isinstance(content, str) and content, f"expected non-empty string content, got {content!r}"
        # The exact fake document text is an internal constant of FakeProvider, not part of the
        # API contract; asserting the whole body would couple this black-box test to that constant.
        # startswith("Введение") is the strongest stable structural assertion for a completed доклад.
        assert content.startswith("Введение"), (
            f"expected completed content to begin with the document's opening section, got {content[:40]!r}"
        )

    def assert_generation_created_pending(self, response: GenerationResponseDto) -> None:
        assert response.status_code == 201, (
            f"expected 201 Created (generation queued without waiting for the LLM call), "
            f"got status_code={response.status_code}, body={response.body}"
        )
        assert response.body is not None, "expected a response body, got None"
        body = response.body

        self._assert_generation_id_is_valid_uuid(body)
        self._assert_created_at_is_recent(body)

        assert body.get("status") == "pending", f"expected status 'pending', got body={body}"
        assert body.get("document_type") == GenerationScope.DEFAULTS["document_type"], (
            f"expected document_type {GenerationScope.DEFAULTS['document_type']!r}, got body={body}"
        )
        assert body.get("topic") == GenerationScope.DEFAULTS["topic"], (
            f"expected topic {GenerationScope.DEFAULTS['topic']!r}, got body={body}"
        )
        assert body.get("volume_pages") == GenerationScope.DEFAULTS["volume_pages"], (
            f"expected volume_pages {GenerationScope.DEFAULTS['volume_pages']!r}, got body={body}"
        )

    def _assert_generation_id_is_valid_uuid(self, body: dict) -> None:
        assert "generation_id" in body, f"expected generation_id in response body, got body={body}"
        try:
            UUID(str(body["generation_id"]))
        except (ValueError, AttributeError, TypeError) as error:
            raise AssertionError(
                f"expected generation_id to be a valid UUID, got {body['generation_id']!r}"
            ) from error

    def _assert_created_at_is_recent(self, body: dict) -> None:
        assert "created_at" in body, f"expected created_at in response body, got body={body}"
        try:
            created_at = datetime.fromisoformat(str(body["created_at"]).replace("Z", "+00:00"))
        except ValueError as error:
            raise AssertionError(
                f"expected created_at to be an ISO-8601 timestamp, got {body['created_at']!r}"
            ) from error
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        assert now - CREATED_AT_MAX_AGE <= created_at <= now + timedelta(seconds=5), (
            f"expected created_at within {CREATED_AT_MAX_AGE} of now ({now.isoformat()}), "
            f"got {created_at.isoformat()}"
        )

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
