from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from generation.generation import Generation
from router.generation.generation_router import (
    router as generation_router,
    get_get_generation_usecase,
)


def _build_generation(status: str, content: str | None) -> Generation:
    return Generation(
        id=uuid4(),
        status=status,
        created_at=datetime(2026, 7, 10, 12, 0, 0, tzinfo=timezone.utc),
        topic="Как работает фотосинтез",
        volume_pages=3,
        requirements=None,
        extra_wishes=None,
        document_type="доклад",
        content=content,
    )


async def _get(app: FastAPI, generation_id):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(f"/api/v1/generations/{generation_id}")


class TestGetGenerationPending:
    """Scenario 4.1: A pending generation reports its status without document content."""

    async def test_should_return_200_with_no_content_field(self, mocker):
        app = FastAPI()
        app.include_router(generation_router)
        generation = _build_generation(status="pending", content=None)
        mock_usecase = mocker.Mock()
        mock_usecase.execute = mocker.AsyncMock(return_value=generation)
        app.dependency_overrides[get_get_generation_usecase] = lambda: mock_usecase

        response = await _get(app, generation.id)

        assert response.status_code == 200, (
            f"expected 200 OK, got {response.status_code} with body {response.text}"
        )
        assert response.json() == {
            "generation_id": str(generation.id),
            "status": "pending",
            "created_at": "2026-07-10T12:00:00Z",
            "topic": "Как работает фотосинтез",
            "volume_pages": 3,
            "document_type": "доклад",
            "content": None,
        }, f"unexpected response body {response.json()}"


class TestGetGenerationCompleted:
    """Scenario 4.2: A completed generation includes the document content."""

    async def test_should_return_200_with_content(self, mocker):
        app = FastAPI()
        app.include_router(generation_router)
        generation = _build_generation(status="completed", content="Готовый доклад")
        mock_usecase = mocker.Mock()
        mock_usecase.execute = mocker.AsyncMock(return_value=generation)
        app.dependency_overrides[get_get_generation_usecase] = lambda: mock_usecase

        response = await _get(app, generation.id)

        assert response.status_code == 200, (
            f"expected 200 OK, got {response.status_code} with body {response.text}"
        )
        assert response.json()["status"] == "completed", (
            f"expected status 'completed', got {response.json()['status']}"
        )
        assert response.json()["content"] == "Готовый доклад", (
            f"expected content 'Готовый доклад', got {response.json()['content']}"
        )


class TestGetGenerationNotFound:
    """Scenario 4.3: Requesting a non-existent generation reports not found."""

    async def test_should_return_404_for_unknown_id(self, mocker):
        app = FastAPI()
        app.include_router(generation_router)
        mock_usecase = mocker.Mock()
        mock_usecase.execute = mocker.AsyncMock(return_value=None)
        app.dependency_overrides[get_get_generation_usecase] = lambda: mock_usecase

        response = await _get(app, uuid4())

        assert response.status_code == 404, (
            f"expected 404 Not Found, got {response.status_code} with body {response.text}"
        )
        assert response.json() == {"detail": "generation not found"}, (
            f"unexpected error body {response.json()}"
        )
