from datetime import UTC, datetime
from uuid import uuid4

from generation.generation import Generation


def _build_generation(status: str, content: str | None, owner_id) -> Generation:
    return Generation(
        id=uuid4(),
        owner_id=owner_id,
        status=status,
        created_at=datetime(2026, 7, 10, 12, 0, 0, tzinfo=UTC),
        topic="Как работает фотосинтез",
        volume_pages=3,
        requirements=None,
        extra_wishes=None,
        document_type="доклад",
        content=content,
    )


class TestGetGenerationPending:
    """Scenario 4.1: A pending generation reports its status without document content."""

    async def test_should_return_200_with_no_content_field(self, mocker, get_client, owner_id):
        generation = _build_generation(status="pending", content=None, owner_id=owner_id)
        mock_usecase = mocker.Mock()
        mock_usecase.execute = mocker.AsyncMock(return_value=generation)

        async with get_client(mock_usecase) as client:
            response = await client.get(f"/api/v1/generations/{generation.id}")

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
            "error_message": None,
        }, f"unexpected response body {response.json()}"
        # The owner reaches the usecase: without it the read would be by id alone,
        # which is the IDOR this task closes. The response deliberately carries no
        # owner field -- you can only ever read your own.
        mock_usecase.execute.assert_awaited_once_with(generation.id, owner_id)


class TestGetGenerationCompleted:
    """Scenario 4.2: A completed generation includes the document content."""

    async def test_should_return_200_with_content(self, mocker, get_client, owner_id):
        generation = _build_generation(status="completed", content="Готовый доклад", owner_id=owner_id)
        mock_usecase = mocker.Mock()
        mock_usecase.execute = mocker.AsyncMock(return_value=generation)

        async with get_client(mock_usecase) as client:
            response = await client.get(f"/api/v1/generations/{generation.id}")

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
    """Scenario 4.3: Requesting a non-existent generation reports not found.

    A generation owned by someone else takes this same branch: the usecase filters
    on owner_id in SQL and answers None either way, so absent and foreign are
    indistinguishable from outside. A 403 would confirm the id exists.
    """

    async def test_should_return_404_for_unknown_id(self, mocker, get_client):
        mock_usecase = mocker.Mock()
        mock_usecase.execute = mocker.AsyncMock(return_value=None)

        async with get_client(mock_usecase) as client:
            response = await client.get(f"/api/v1/generations/{uuid4()}")

        assert response.status_code == 404, (
            f"expected 404 Not Found, got {response.status_code} with body {response.text}"
        )
        assert response.json() == {"detail": "generation not found"}, (
            f"unexpected error body {response.json()}"
        )
