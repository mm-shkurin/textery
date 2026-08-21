"""«Удалить текст из истории» — the one operation on this screen that cannot be undone."""

from uuid import uuid4

import pytest

from document.delete_document import DeleteDocument
from shared.exceptions import NotFoundException
from statements.document_fakes import FakeUnitOfWork, seeded, stored_document


def _usecase(repository, unit_of_work):
    return DeleteDocument(document_repository=repository, unit_of_work=unit_of_work)


class TestDeleteDocument:
    async def test_should_remove_the_callers_own_document(self):
        owner_id = uuid4()
        document = stored_document(owner_id=owner_id)
        repository = await seeded(document)
        unit_of_work = FakeUnitOfWork()

        await _usecase(repository, unit_of_work).execute(document.id, owner_id)

        assert repository.documents == [], "the row the caller named must be gone"

    async def test_should_commit_once_the_row_is_gone(self):
        owner_id = uuid4()
        document = stored_document(owner_id=owner_id)
        unit_of_work = FakeUnitOfWork()

        await _usecase(await seeded(document), unit_of_work).execute(document.id, owner_id)

        # Without the commit the DELETE is rolled back with the session and the row reappears on
        # the next read — a delete that reports success and changes nothing.
        assert unit_of_work.commit_call_count == 1

    async def test_should_refuse_a_document_that_does_not_exist(self):
        repository = await seeded()

        with pytest.raises(NotFoundException):
            await _usecase(repository, FakeUnitOfWork()).execute(uuid4(), uuid4())

    async def test_should_answer_a_foreign_document_exactly_as_an_absent_one(self):
        # Indistinguishable ON PURPOSE. Two different answers would let a caller enumerate which
        # document ids are real by reading the difference between them.
        someone_else = stored_document(owner_id=uuid4())
        repository = await seeded(someone_else)

        with pytest.raises(NotFoundException):
            await _usecase(repository, FakeUnitOfWork()).execute(someone_else.id, uuid4())

        assert repository.documents == [someone_else], "a foreign document must survive untouched"

    async def test_should_not_commit_when_nothing_was_deleted(self):
        unit_of_work = FakeUnitOfWork()

        with pytest.raises(NotFoundException):
            await _usecase(await seeded(), unit_of_work).execute(uuid4(), uuid4())

        # Raised BEFORE the commit, so the transaction is abandoned rather than committed empty —
        # otherwise the failure path looks successful to anything watching for commits.
        assert unit_of_work.commit_call_count == 0
