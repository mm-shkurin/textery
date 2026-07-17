from datetime import datetime, timezone
from uuid import uuid4

from generation.generation import Generation


class TestCreateGenerationHappyPath:
    """Scenario 2.1: Valid request is accepted and queued without waiting on the LLM call."""

    async def test_should_return_201_with_pending_generation_and_enqueue_background_task(
        self, mocker, create_client, owner_id
    ):
        generation = Generation(
            id=uuid4(),
            owner_id=owner_id,
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

        async with create_client(mock_request_usecase, mock_generate_document) as client:
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
            "topic": "Как работает фотосинтез",
            "volume_pages": 3,
            "document_type": "доклад",
        }, f"unexpected response body {response.json()}"
        # owner_id comes from the token, never the body -- a client that sent one
        # would have it ignored by Pydantic's extra="ignore".
        mock_request_usecase.execute.assert_awaited_once_with(
            owner_id=owner_id,
            topic="Как работает фотосинтез",
            volume_pages=3,
            requirements=None,
            extra_wishes=None,
            document_type="доклад",
        )
        # The background task carries the owner too: it re-reads through the
        # owner-filtered query, so an id alone would find nothing and the generation
        # would sit pending forever.
        mock_generate_document.execute.assert_awaited_once_with(generation.id, owner_id)
