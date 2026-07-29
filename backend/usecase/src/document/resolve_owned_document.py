from uuid import UUID

from document.document_repository import DocumentRepository
from document.document_scope import DocumentScope
from shared.exceptions import NotFoundException

# The one canonical refusal body for all seven AI-edit endpoints. It names no
# document and carries no instruction text: `not_found_exception_handler` logs
# the exception verbatim at INFO, and the whole premise of a refused request is
# that the caller has no claim to that id.
REFUSAL_MESSAGE = "document not found"


async def resolve_owned_document(
    document_repository: DocumentRepository,
    document_id: UUID,
    owner_id: UUID,
) -> DocumentScope:
    """Resolve a document the caller owns, or refuse as not found.

    The first statement of all seven story-19 usecases. A foreign document and an
    absent one must be refused identically, so this raises the same exception with
    the same text for both -- and carries no document id, which would otherwise
    reach the logs of a request whose whole point is that the caller has no claim
    to that id.
    """
    scope = await document_repository.find_scope_by_id_and_owner(document_id, owner_id)
    if scope is None:
        raise NotFoundException(REFUSAL_MESSAGE)
    return scope
