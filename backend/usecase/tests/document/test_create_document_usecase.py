from uuid import uuid4

import pytest

from document.create_document import CreateDocument
from document.document import DRAFT_STATUS
from shared.exceptions import ValidationException
from statements.document_fakes import FakeClock, FakeDocumentRepository, FakeUnitOfWork


def build(repository=None, unit_of_work=None):
    return CreateDocument(
        document_repository=repository or FakeDocumentRepository(),
        clock=FakeClock(),
        unit_of_work=unit_of_work or FakeUnitOfWork(),
    )


class TestCreateDocumentHappyPath:
    """Scenario 2.1: creating a manual document returns immediately, empty, no Generation."""

    async def test_should_create_an_empty_draft_owned_by_the_caller(self):
        repository = FakeDocumentRepository()
        owner_id = uuid4()

        result = await build(repository).execute(
            owner_id=owner_id, document_type="эссе", idempotency_key="key-1"
        )

        assert result.is_replay is False, "a first create is not a replay"
        assert result.document.owner_id == owner_id, (
            "the owner comes from the caller, never the body"
        )
        assert result.document.document_type == "эссе"
        assert result.document.status == DRAFT_STATUS
        assert result.document.content == ""
        assert result.document.version == 1
        assert repository.documents == [result.document], "exactly one document is persisted"

    async def test_should_commit_once(self):
        unit_of_work = FakeUnitOfWork()

        await build(unit_of_work=unit_of_work).execute(
            owner_id=uuid4(), document_type="доклад", idempotency_key="key-1"
        )

        assert unit_of_work.commit_call_count == 1, "the create must be durable"
        assert unit_of_work.rollback_call_count == 0


class TestCreateDocumentValidation:
    """Scenario 1.1: reject an unsupported document type."""

    async def test_should_reject_an_unsupported_document_type(self):
        repository = FakeDocumentRepository()

        with pytest.raises(ValidationException) as excinfo:
            await build(repository).execute(
                owner_id=uuid4(), document_type="диссертация", idempotency_key="key-1"
            )

        assert excinfo.value.error_code == "INVALID_DOCUMENT_TYPE"
        assert repository.documents == [], "no document is created for an invalid type"

    async def test_should_reject_an_idempotency_key_that_is_too_long(self):
        repository = FakeDocumentRepository()

        with pytest.raises(ValidationException) as excinfo:
            await build(repository).execute(
                owner_id=uuid4(), document_type="эссе", idempotency_key="k" * 129
            )

        assert excinfo.value.error_code == "INVALID_IDEMPOTENCY_KEY"
        assert repository.documents == []


class TestCreateDocumentIdempotency:
    """Scenario 3.1: replaying the same key returns the original, never a duplicate."""

    async def test_should_return_the_original_document_when_the_key_is_replayed(self):
        repository = FakeDocumentRepository()
        owner_id = uuid4()
        usecase = build(repository)
        first = await usecase.execute(
            owner_id=owner_id, document_type="эссе", idempotency_key="key-1"
        )

        replay = await usecase.execute(
            owner_id=owner_id, document_type="эссе", idempotency_key="key-1"
        )

        assert replay.is_replay is True, "the router needs this to answer 200 rather than 201"
        assert replay.document.id == first.document.id, (
            "the replay must refer to the original document"
        )
        assert len(repository.documents) == 1, "exactly one document exists for that key"

    async def test_should_return_the_original_even_when_the_replay_asks_for_another_type(self):
        # The key identifies the logical create, not the body -- that is what makes it
        # a retry token. Answering 409 would strand a client that retried with a
        # corrected body: permanent error, no way forward.
        repository = FakeDocumentRepository()
        owner_id = uuid4()
        usecase = build(repository)
        first = await usecase.execute(
            owner_id=owner_id, document_type="эссе", idempotency_key="key-1"
        )

        replay = await usecase.execute(
            owner_id=owner_id, document_type="реферат", idempotency_key="key-1"
        )

        assert replay.document.id == first.document.id
        assert replay.document.document_type == "эссе", (
            "the original type wins; the replay does not mutate"
        )
        assert len(repository.documents) == 1

    async def test_should_give_two_owners_separate_documents_for_the_same_key(self):
        # Security 7.3. A global key namespace would return one account another
        # account's document -- the IDOR re-entering through the idempotency door.
        repository = FakeDocumentRepository()
        usecase = build(repository)

        first = await usecase.execute(
            owner_id=uuid4(), document_type="эссе", idempotency_key="shared"
        )
        second = await usecase.execute(
            owner_id=uuid4(), document_type="эссе", idempotency_key="shared"
        )

        assert first.document.id != second.document.id
        assert second.is_replay is False, "another owner's key is not a replay"
        assert len(repository.documents) == 2
