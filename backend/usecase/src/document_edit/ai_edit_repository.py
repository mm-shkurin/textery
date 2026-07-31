from typing import Protocol
from uuid import UUID

from document_edit.ai_edit_scope import AiEditScope


class AiEditRepository(Protocol):
    """Port for AI-edit persistence.

    There is deliberately **no** `find_by_id(edit_id)`: the path document id is
    authoritative, so the edit is only ever looked up together with the document
    it must belong to. An unscoped finder alongside this one would be one
    autocomplete away from serving an edit under a document that does not own it
    -- the same rule `DocumentRepository` carries for ownership.

    The bodies raise rather than `...`: a `...` body on an `async def` is a
    concrete coroutine returning `None`, so an adapter that forgot to implement
    the method would silently answer "not found" instead of failing loudly.

    The scoping ids are keyword-only, the same rule `resolve_owned_edit` applies
    to its own signature. Two same-typed UUIDs in a row transpose silently: the
    call type-checks and resolves the wrong pair rather than failing, which on
    the one port whose entire job is scoping is an authorization defect that
    never reaches a stack trace. The rule has to hold at the boundary it guards,
    not stop one frame short of it.
    """

    async def find_scope_by_id_and_document(
        self, *, edit_id: UUID, document_id: UUID
    ) -> AiEditScope | None:
        """The document-scoped existence check, without the edit body.

        Returns `None` for both an absent edit and an edit belonging to another
        document -- the caller renders them identically, so the distinction must
        not survive the port.
        """
        raise NotImplementedError(
            "AiEditRepository.find_scope_by_id_and_document"
        )
