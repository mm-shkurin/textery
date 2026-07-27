from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from document.document import Document

CREATED_AT = datetime(2026, 7, 17, 12, 0, tzinfo=UTC)


def a_document(owner_id: UUID, content: str = "", version: int = 1) -> Document:
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


class TestSaveDocumentTitleRoute:
    """Scenario 3.1: a title in the save body must reach SaveDocument.execute.

    The exported filename is derived from the document title, so a save carrying a
    title has to forward it to the usecase. Today the PUT route reads only content
    and version, and SaveDocumentRequestDto's default extra="ignore" silently drops
    the title field before the route ever sees it.
    """

    @pytest.mark.skip(
        reason="RED 3.1: save route drops title -- SaveDocumentRequestDto has no "
        "title field (extra=ignore) and the PUT route never forwards it to "
        "SaveDocument.execute. Un-skip in green-adapter rest."
    )
    async def test_should_forward_the_title_to_the_save_usecase(
        self, mocker, save_client, owner_id
    ):
        document = a_document(owner_id, content="<p>saved</p>", version=2)
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(return_value=document)

        async with save_client(usecase) as client:
            response = await client.put(
                f"/api/v1/documents/{document.id}",
                json={
                    "content": "<p>saved</p>",
                    "version": 1,
                    "title": "Привет Мир",
                },
            )

        assert response.status_code == 200, f"got {response.status_code}: {response.text}"
        usecase.execute.assert_awaited_once_with(
            document_id=document.id,
            owner_id=owner_id,
            content="<p>saved</p>",
            version=1,
            title="Привет Мир",
        )
