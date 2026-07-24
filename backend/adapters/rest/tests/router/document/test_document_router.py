from datetime import UTC, datetime
from uuid import UUID, uuid4

from document.document import Document
from document.document_creation_result import DocumentCreationResult

CREATED_AT = datetime(2026, 7, 17, 12, 0, tzinfo=UTC)


def a_document(owner_id: UUID, content: str = "", version: int = 1) -> Document:
    """A stored document owned by the account the Bearer override resolves to.

    The owner is a parameter, not a module constant read from `conftest`: three
    conftest modules sit on this suite's import path, so `from conftest import
    OWNER_ID` binds whichever one landed there first -- possibly a different
    constant than the fixture the client override actually uses. The generation
    slice's conftest documents that hazard; this file was doing it anyway.
    """
    return Document.reconstitute(
        id=uuid4(),
        owner_id=owner_id,
        document_type="эссе",
        status="draft",
        content=content,
        version=version,
        idempotency_key="key-1",
        created_at=CREATED_AT,
        updated_at=CREATED_AT,
    )


class TestCreateDocumentRoute:
    """Scenario 2.1 / 3.1: 201 on create, 200 on a replayed key."""

    async def test_should_return_201_and_the_document_on_a_fresh_create(
        self, mocker, create_client, owner_id
    ):
        document = a_document(owner_id)
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(
            return_value=DocumentCreationResult(document=document, is_replay=False)
        )

        async with create_client(usecase) as client:
            response = await client.post(
                "/api/v1/documents",
                json={"document_type": "эссе"},
                headers={"Idempotency-Key": "key-1"},
            )

        assert response.status_code == 201, f"got {response.status_code}: {response.text}"
        assert response.json() == {
            "document_id": str(document.id),
            "document_type": "эссе",
            "status": "draft",
            "content": "",
            "version": 1,
            "created_at": "2026-07-17T12:00:00Z",
            "updated_at": "2026-07-17T12:00:00Z",
        }, f"unexpected body {response.json()}"
        usecase.execute.assert_awaited_once_with(
            owner_id=owner_id, document_type="эссе", idempotency_key="key-1"
        )

    async def test_should_return_200_when_the_key_was_replayed(
        self, mocker, create_client, owner_id
    ):
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(
            return_value=DocumentCreationResult(document=a_document(owner_id), is_replay=True)
        )

        async with create_client(usecase) as client:
            response = await client.post(
                "/api/v1/documents",
                json={"document_type": "эссе"},
                headers={"Idempotency-Key": "key-1"},
            )

        assert response.status_code == 200, (
            f"a replay must be 200, not 201 — the client uses the distinction to know it did not "
            f"create a second document. Got {response.status_code}: {response.text}"
        )

    async def test_should_ignore_server_owned_fields_in_the_body(
        self, mocker, create_client, owner_id
    ):
        # Scenario 1.2 / Security 2.1. The usecase must be called with the type only;
        # the attacker's status/id/content never reach it.
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(
            return_value=DocumentCreationResult(document=a_document(owner_id), is_replay=False)
        )

        async with create_client(usecase) as client:
            response = await client.post(
                "/api/v1/documents",
                json={
                    "document_type": "эссе",
                    "status": "completed",
                    "id": str(uuid4()),
                    "content": "<p>injected</p>",
                },
                headers={"Idempotency-Key": "key-1"},
            )

        assert response.status_code == 201, (
            f"extra fields are dropped, not rejected: {response.text}"
        )
        usecase.execute.assert_awaited_once_with(
            owner_id=owner_id, document_type="эссе", idempotency_key="key-1"
        )
        assert response.json()["status"] == "draft"
        assert response.json()["content"] == ""


class TestGetDocumentRoute:
    async def test_should_return_200_with_the_document(self, mocker, get_client, owner_id):
        document = a_document(owner_id, content="<p>текст</p>", version=3)
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(return_value=document)

        async with get_client(usecase) as client:
            response = await client.get(f"/api/v1/documents/{document.id}")

        assert response.status_code == 200, f"got {response.status_code}: {response.text}"
        assert response.json()["content"] == "<p>текст</p>"
        assert response.json()["version"] == 3
        usecase.execute.assert_awaited_once_with(document_id=document.id, owner_id=owner_id)

    async def test_should_return_404_when_the_usecase_finds_nothing(self, mocker, get_client):
        # Scenario 4.2 and Security 7.1 are the same code path: absent and foreign
        # both arrive here as None, so they cannot produce different answers.
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(return_value=None)

        async with get_client(usecase) as client:
            response = await client.get(f"/api/v1/documents/{uuid4()}")

        assert response.status_code == 404, f"got {response.status_code}: {response.text}"
        assert response.json() == {
            "error_code": "NOT_FOUND",
            "message": "The requested resource was not found.",
        }


class TestSaveDocumentRoute:
    async def test_should_return_200_with_the_stored_document(self, mocker, save_client, owner_id):
        document = a_document(owner_id, content="<p>saved</p>", version=2)
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(return_value=document)

        async with save_client(usecase) as client:
            response = await client.put(
                f"/api/v1/documents/{document.id}",
                json={"content": "<p>saved</p>", "version": 1},
            )

        assert response.status_code == 200, f"got {response.status_code}: {response.text}"
        assert response.json()["version"] == 2
        usecase.execute.assert_awaited_once_with(
            document_id=document.id, owner_id=owner_id, content="<p>saved</p>", version=1
        )

    async def test_should_ignore_server_owned_fields_in_the_save_body(
        self, mocker, save_client, owner_id
    ):
        # Scenario 5.4: only content and version are ever applied.
        document = a_document(owner_id, version=2)
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(return_value=document)

        async with save_client(usecase) as client:
            response = await client.put(
                f"/api/v1/documents/{document.id}",
                json={
                    "content": "<p>x</p>",
                    "version": 1,
                    "document_type": "реферат",
                    "id": str(uuid4()),
                    "status": "completed",
                },
            )

        assert response.status_code == 200, f"got {response.status_code}: {response.text}"
        usecase.execute.assert_awaited_once_with(
            document_id=document.id, owner_id=owner_id, content="<p>x</p>", version=1
        )
