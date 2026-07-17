from datetime import UTC, datetime
from uuid import uuid4

from document.document import Document
from shared.page import DEFAULT_LIMIT, Page

_LONG_CONTENT = "<p>" + ("x" * 1000) + "</p>"


def _document(owner_id) -> Document:
    stamp = datetime(2026, 7, 17, 12, 0, 0, tzinfo=UTC)
    return Document(
        id=uuid4(),
        owner_id=owner_id,
        document_type="доклад",
        status="draft",
        content=_LONG_CONTENT,
        version=3,
        idempotency_key="key-1",
        created_at=stamp,
        updated_at=stamp,
    )


class TestListDocuments:
    """History: the caller's own documents, newest created first."""

    async def test_should_return_a_page_of_summaries(self, mocker, list_client, owner_id):
        document = _document(owner_id)
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(
            return_value=Page(items=[document], next_cursor="next-anchor")
        )

        async with list_client(usecase) as client:
            response = await client.get("/api/v1/documents")

        assert response.status_code == 200, f"got {response.status_code}: {response.text}"
        assert response.json() == {
            "items": [
                {
                    "document_id": str(document.id),
                    "document_type": "доклад",
                    "status": "draft",
                    "version": 3,
                    "created_at": "2026-07-17T12:00:00Z",
                    "updated_at": "2026-07-17T12:00:00Z",
                }
            ],
            "next_cursor": "next-anchor",
        }, f"unexpected body {response.json()}"

    async def test_should_not_leak_content_into_the_list(self, mocker, list_client, owner_id):
        # documents_save.yaml caps content at 200,000 characters. A 20-item page of
        # full documents is a multi-megabyte response for a screen showing titles;
        # the editor fetches the one it opens via GET /documents/{id}.
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(
            return_value=Page(items=[_document(owner_id)], next_cursor=None)
        )

        async with list_client(usecase) as client:
            response = await client.get("/api/v1/documents")

        item = response.json()["items"][0]
        assert "content" not in item, f"list items must carry no content, got {item}"
        assert _LONG_CONTENT not in response.text, "content must not reach the wire at all"

    async def test_should_pass_the_callers_owner_and_paging_through(
        self, mocker, list_client, owner_id
    ):
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(return_value=Page(items=[], next_cursor=None))

        async with list_client(usecase) as client:
            await client.get("/api/v1/documents?limit=5&cursor=anchor")

        usecase.execute.assert_awaited_once_with(owner_id=owner_id, limit=5, cursor="anchor")

    async def test_should_default_paging_when_unspecified(self, mocker, list_client, owner_id):
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(return_value=Page(items=[], next_cursor=None))

        async with list_client(usecase) as client:
            await client.get("/api/v1/documents")

        usecase.execute.assert_awaited_once_with(
            owner_id=owner_id, limit=DEFAULT_LIMIT, cursor=None
        )

    async def test_should_not_be_swallowed_by_the_by_id_route(self, mocker, list_client):
        # GET "" and GET "/{document_id}" are distinct paths, but a regression that
        # made the parameterised one match the bare collection would answer 422 on a
        # UUID parse rather than list anything.
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(return_value=Page(items=[], next_cursor=None))

        async with list_client(usecase) as client:
            response = await client.get("/api/v1/documents")

        assert response.status_code == 200, (
            f"the collection route must handle this, got {response.status_code}: {response.text}"
        )


class TestListDocumentsRequiresBearer:
    async def test_should_return_401_without_an_authorization_header(
        self, mocker, unauthenticated_list_client
    ):
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock()

        async with unauthenticated_list_client(usecase) as client:
            response = await client.get("/api/v1/documents")

        assert response.status_code == 401, f"got {response.status_code}: {response.text}"
        assert response.json()["error_code"] == "UNAUTHORIZED"
        usecase.execute.assert_not_awaited(), "no history may be read without a token"
