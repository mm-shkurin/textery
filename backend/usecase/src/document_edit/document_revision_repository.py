from typing import Protocol
from uuid import UUID

from document_edit.revision_scope import RevisionScope


class DocumentRevisionRepository(Protocol):
    """Port for document-revision persistence.

    There is deliberately **no** `find_by_number(n)`: revision numbers are
    per-document, so a finder taking the number alone does not identify a row at
    all -- it identifies one row per document in the system. The path document id
    is authoritative, so the revision is only ever looked up together with the
    document it must belong to. Same rule `DocumentRepository` and
    `AiEditRepository` already carry.

    The body raises rather than `...`: a `...` body on an `async def` is a
    concrete coroutine returning `None`, so an adapter that forgot to implement
    the method would silently answer "not found" for every owner's own revision.

    The scoping arguments are keyword-only. Unlike the edit port the two are not
    same-typed, but the rule is the port's contract rather than a reaction to one
    call site's hazard, and `resolve_owned_revision` applies it to itself.
    """

    async def find_scope_by_number_and_document(
        self, *, revision_number: int, document_id: UUID
    ) -> RevisionScope | None:
        """The document-scoped existence check, without the revision body.

        Returns `None` for both an absent revision number and a number that
        belongs to another document -- the caller renders them identically, so the
        distinction must not survive the port.
        """
        raise NotImplementedError("DocumentRevisionRepository.find_scope_by_number_and_document")
