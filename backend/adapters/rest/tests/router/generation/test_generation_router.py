import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from router.generation.generation_router import router as generation_router, get_generation_usecase
from error_handling.exception_handlers import validation_exception_handler
from shared.exceptions import ValidationException

EXPECTED_MISSING_TOPIC_MESSAGE = "topic is required"


@pytest.mark.skip(
    reason="RED: backend/adapters/rest/src has no generation router yet -- "
    "ModuleNotFoundError: No module named 'router.generation.generation_router'"
)
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
        app.dependency_overrides[get_generation_usecase] = lambda: mock_usecase

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
        assert response.json() == {"detail": EXPECTED_MISSING_TOPIC_MESSAGE}, (
            f"expected error body {{'detail': '{EXPECTED_MISSING_TOPIC_MESSAGE}'}}, "
            f"got {response.json()}"
        )
