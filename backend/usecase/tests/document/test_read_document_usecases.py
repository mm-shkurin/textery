"""The document read side: GetDocument and ListDocuments.

Both were exercised only through the router before, where the usecase itself is
replaced by a stub — so the owner predicate, the has-next probe and the cursor
hand-off had no test that ran the real code. Every assertion here would survive
the router being deleted.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from document.document import Document
from document.get_document import GetDocument
from document.list_documents import ListDocuments
from shared.exceptions import ValidationException
from shared.keyset_cursor import KeysetCursor
from statements.document_fakes import FakeDocumentRepository

_EPOCH = datetime(2026, 7, 17, 12, 0, tzinfo=UTC)


def stored_document(owner_id: UUID, minutes_old: int = 0) -> Document:
    """A persisted draft, `minutes_old` minutes older than the newest possible one."""
    return Document(
        id=uuid4(),
        owner_id=owner_id,
        document_type="эссе",
        status="draft",
        content="",
        version=1,
        idempotency_key=f"key-{uuid4()}",
        created_at=_EPOCH - timedelta(minutes=minutes_old),
        updated_at=_EPOCH - timedelta(minutes=minutes_old),
    )


async def seeded(*documents: Document) -> FakeDocumentRepository:
    repository = FakeDocumentRepository()
    for document in documents:
        await repository.save_new(document)
    return repository


class TestGetDocument:
    async def test_should_return_the_callers_own_document(self):
        owner_id = uuid4()
        document = stored_document(owner_id)

        found = await GetDocument(await seeded(document)).execute(
            document_id=document.id, owner_id=owner_id
        )

        assert found is document, "the caller's own document is returned as stored"

    async def test_should_answer_none_for_another_owners_document(self):
        document = stored_document(uuid4())

        found = await GetDocument(await seeded(document)).execute(
            document_id=document.id, owner_id=uuid4()
        )

        # Identical to the absent answer below, deliberately: distinguishing them
        # would confirm the id exists to a caller who does not own it.
        assert found is None, "a foreign document is not readable by id alone"

    async def test_should_answer_none_for_an_unknown_document(self):
        found = await GetDocument(FakeDocumentRepository()).execute(
            document_id=uuid4(), owner_id=uuid4()
        )

        assert found is None


class TestListDocumentsOwnerScoping:
    async def test_should_return_only_the_callers_documents_newest_first(self):
        owner_id = uuid4()
        newest = stored_document(owner_id, minutes_old=0)
        oldest = stored_document(owner_id, minutes_old=10)
        foreign = stored_document(uuid4(), minutes_old=5)

        page = await ListDocuments(await seeded(oldest, foreign, newest)).execute(owner_id=owner_id)

        assert page.items == [newest, oldest], "another owner's document never appears"
        assert page.next_cursor is None, "a single full page has no next anchor"


class TestListDocumentsPaging:
    async def test_should_trim_the_probe_row_and_emit_a_cursor_when_more_remain(self):
        owner_id = uuid4()
        newest = stored_document(owner_id, minutes_old=0)
        middle = stored_document(owner_id, minutes_old=1)
        oldest = stored_document(owner_id, minutes_old=2)
        repository = await seeded(newest, middle, oldest)

        page = await ListDocuments(repository).execute(owner_id=owner_id, limit=2)

        assert page.items == [newest, middle], "limit rows exactly — the probe row is trimmed"
        assert page.next_cursor is not None, "a third row exists, so paging continues"
        anchor = KeysetCursor.decode(page.next_cursor)
        assert anchor.id == middle.id, "the anchor is the last row served, not the probe row"

    async def test_should_resume_strictly_after_the_cursor(self):
        owner_id = uuid4()
        newest = stored_document(owner_id, minutes_old=0)
        middle = stored_document(owner_id, minutes_old=1)
        oldest = stored_document(owner_id, minutes_old=2)
        usecase = ListDocuments(await seeded(newest, middle, oldest))

        first = await usecase.execute(owner_id=owner_id, limit=2)
        second = await usecase.execute(owner_id=owner_id, limit=2, cursor=first.next_cursor)

        assert second.items == [oldest], "the second page starts after the anchor, not on it"
        assert second.next_cursor is None, "the last page emits no cursor to loop on"

    async def test_should_reject_a_limit_above_the_bound(self):
        with pytest.raises(ValidationException) as excinfo:
            await ListDocuments(FakeDocumentRepository()).execute(owner_id=uuid4(), limit=101)

        assert excinfo.value.error_code == "INVALID_LIMIT"

    async def test_should_reject_an_undecodable_cursor(self):
        with pytest.raises(ValidationException) as excinfo:
            await ListDocuments(FakeDocumentRepository()).execute(
                owner_id=uuid4(), cursor="not-a-cursor"
            )

        assert excinfo.value.error_code == "INVALID_CURSOR"
