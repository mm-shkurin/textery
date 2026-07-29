from dataclasses import dataclass
from uuid import UUID

from document.document_repository import DocumentRepository


@dataclass(frozen=True)
class DocumentScope:
    """A bounded projection of a document, for callers that only need to know it
    exists and is theirs.

    Deliberately not `Document`: nothing on the guard path needs `content`, and a
    200 000-code-point field materialised on every request to all seven AI-edit
    endpoints answers a yes/no question at the cost of the largest column in the
    schema. See decisions/document-scope-guard-decision.md.
    """

    id: UUID
    owner_id: UUID


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
    raise NotImplementedError()
