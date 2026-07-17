from datetime import UTC, datetime
from uuid import uuid4

from generation.generation import Generation
from shared.page import DEFAULT_LIMIT, Page


def _generation(owner_id) -> Generation:
    return Generation(
        id=uuid4(),
        owner_id=owner_id,
        status="completed",
        created_at=datetime(2026, 7, 17, 12, 0, 0, tzinfo=UTC),
        topic="Как работает фотосинтез",
        volume_pages=3,
        requirements=None,
        extra_wishes=None,
        document_type="доклад",
        content="Готовый доклад",
    )


class TestListGenerations:
    """History: the caller's own generations, newest first."""

    async def test_should_return_a_page_of_summaries(self, mocker, list_client, owner_id):
        generation = _generation(owner_id)
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(
            return_value=Page(items=[generation], next_cursor="next-anchor")
        )

        async with list_client(usecase) as client:
            response = await client.get("/api/v1/generations")

        assert response.status_code == 200, f"got {response.status_code}: {response.text}"
        assert response.json() == {
            "items": [
                {
                    "generation_id": str(generation.id),
                    "status": "completed",
                    "created_at": "2026-07-17T12:00:00Z",
                    "topic": "Как работает фотосинтез",
                    "volume_pages": 3,
                    "document_type": "доклад",
                }
            ],
            "next_cursor": "next-anchor",
        }, f"unexpected body {response.json()}"

    async def test_should_not_leak_content_into_the_list(self, mocker, list_client, owner_id):
        # The summary projection is the point: a page of full documents is megabytes
        # for a screen that renders titles. The editor fetches content per id.
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(
            return_value=Page(items=[_generation(owner_id)], next_cursor=None)
        )

        async with list_client(usecase) as client:
            response = await client.get("/api/v1/generations")

        assert "content" not in response.json()["items"][0], (
            f"list items must carry no content, got {response.json()['items'][0]}"
        )

    async def test_should_pass_the_callers_owner_and_paging_through(
        self, mocker, list_client, owner_id
    ):
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(return_value=Page(items=[], next_cursor=None))

        async with list_client(usecase) as client:
            await client.get("/api/v1/generations?limit=5&cursor=anchor")

        # owner_id comes from the token, never a query parameter -- a caller cannot
        # ask for someone else's history by passing an id.
        usecase.execute.assert_awaited_once_with(owner_id=owner_id, limit=5, cursor="anchor")

    async def test_should_default_paging_when_unspecified(self, mocker, list_client, owner_id):
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(return_value=Page(items=[], next_cursor=None))

        async with list_client(usecase) as client:
            await client.get("/api/v1/generations")

        usecase.execute.assert_awaited_once_with(
            owner_id=owner_id, limit=DEFAULT_LIMIT, cursor=None
        )

    async def test_should_return_an_empty_page_for_no_history(self, mocker, list_client):
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(return_value=Page(items=[], next_cursor=None))

        async with list_client(usecase) as client:
            response = await client.get("/api/v1/generations")

        assert response.json() == {"items": [], "next_cursor": None}, (
            f"unexpected body {response.json()}"
        )


class TestListGenerationsRequiresBearer:
    async def test_should_return_401_without_an_authorization_header(
        self, mocker, unauthenticated_list_client
    ):
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock()

        async with unauthenticated_list_client(usecase) as client:
            response = await client.get("/api/v1/generations")

        assert response.status_code == 401, f"got {response.status_code}: {response.text}"
        assert response.json()["error_code"] == "UNAUTHORIZED"
        usecase.execute.assert_not_awaited(), "no history may be read without a token"
