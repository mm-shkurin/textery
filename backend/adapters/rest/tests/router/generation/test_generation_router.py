import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from router.generation.generation_router import (
    router as generation_router,
    get_generate_document_usecase,
    get_request_generation_usecase,
)
from error_handling.exception_handlers import validation_exception_handler
from shared.exceptions import ValidationException

EXPECTED_MISSING_TOPIC_MESSAGE = "topic is required"


class TestCreateGenerationRouter:
    """Scenario 1.1: Reject request with missing topic.

    Given a generation request without a topic
    When the client submits the request
    Then the response is a validation error
    And no generation is created
    """

    async def test_should_reject_missing_topic_with_400(self, mocker):
        app = FastAPI()
        app.include_router(generation_router)
        app.add_exception_handler(ValidationException, validation_exception_handler)

        mock_usecase = mocker.Mock()
        mock_usecase.execute = mocker.AsyncMock(
            side_effect=ValidationException(EXPECTED_MISSING_TOPIC_MESSAGE)
        )
        app.dependency_overrides[get_request_generation_usecase] = lambda: mock_usecase
        app.dependency_overrides[get_generate_document_usecase] = lambda: mocker.Mock()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/generations",
                json={"document_type": "доклад", "volume_pages": 3},
                headers={"Idempotency-Key": "test-key"},
            )

        assert response.status_code == 400, (
            f"expected 400 Bad Request for missing topic, got {response.status_code} "
            f"with body {response.text}"
        )
        assert response.json() == {
            "error_code": "VALIDATION_ERROR",
            "message": EXPECTED_MISSING_TOPIC_MESSAGE,
        }, (
            f"expected error body {{'error_code': 'VALIDATION_ERROR', 'message': '{EXPECTED_MISSING_TOPIC_MESSAGE}'}}, "
            f"got {response.json()}"
        )
