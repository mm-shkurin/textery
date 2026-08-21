from uuid import UUID

from document.document_repository import DocumentRepository
from shared.exceptions import NotFoundException
from shared.unit_of_work import UnitOfWork


class DeleteDocument:
    """Remove one of the caller's own documents from their history.

    A top-level operation, not a step inside another: «удалить текст из истории»
    is a user-visible action with its own authorization and its own transaction,
    and nothing else in the app deletes a document.

    Absent and foreign are ONE answer. The repository filters on `owner_id` in
    SQL, so a document belonging to someone else matches zero rows and is
    reported exactly as a document that never existed — a caller must not be able
    to probe which ids are real by reading the difference between two errors.
    """

    def __init__(self, document_repository: DocumentRepository, unit_of_work: UnitOfWork) -> None:
        self._document_repository = document_repository
        self._unit_of_work = unit_of_work

    async def execute(self, document_id: UUID, owner_id: UUID) -> None:
        deleted = await self._document_repository.delete_by_id_and_owner(document_id, owner_id)
        if not deleted:
            # Raised BEFORE the commit, so the transaction is abandoned rather
            # than committed empty. Committing a no-op costs a round trip and,
            # more to the point, would make the failure path look successful in
            # any log that watches for commits.
            raise NotFoundException(f"document {document_id} not found")
        await self._unit_of_work.commit()
