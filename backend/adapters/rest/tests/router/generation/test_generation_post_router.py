from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from generation.generation import Generation
from router.generation.generation_router import (
    router as generation_router,
    get_generate_document_usecase,
    get_request_generation_usecase,
)


class TestCreateGenerationHappyPath:
    """Scenario 2.1: Valid request is accepted and queued without waiting on the LLM call."""

    async def test_should_return_201_with_pending_generation_and_enqueue_background_task(self, mocker):
        app = FastAPI()
        app.include_router(generation_router)

        generation = Generation(
            id=uuid4(),
            status="pending",
            created_at=datetime(2026, 7, 10, 12, 0, 0, tzinfo=timezone.utc),
            topic="Как работает фотосинтез",
            volume_pages=3,
            requirements=None,
            extra_wishes=None,
            document_type="доклад",
            content=None,
        )
        mock_request_usecase = mocker.Mock()
        mock_request_usecase.execute = mocker.AsyncMock(return_value=generation)
        mock_generate_document = mocker.Mock()
        mock_generate_document.execute = mocker.AsyncMock()
        app.dependency_overrides[get_request_generation_usecase] = lambda: mock_request_usecase
        app.dependency_overrides[get_generate_document_usecase] = lambda: mock_generate_document

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/generations",
                json={
                    "document_type": "доклад",
                    "topic": "Как работает фотосинтез",
                    "volume_pages": 3,
                },
                headers={"Idempotency-Key": "test-key"},
            )

        assert response.status_code == 201, (
            f"expected 201 Created, got {response.status_code} with body {response.text}"
        )
        assert response.json() == {
            "generation_id": str(generation.id),
            "status": "pending",
            "created_at": "2026-07-10T12:00:00Z",
        }, f"unexpected response body {response.json()}"
        mock_request_usecase.execute.assert_awaited_once_with(
            topic="Как работает фотосинтез",
            volume_pages=3,
            requirements=None,
            extra_wishes=None,
            document_type="доклад",
        )
        mock_generate_document.execute.assert_awaited_once_with(generation.id)
