from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class DocumentScope:
    """A bounded projection of a document, for callers that only need to know it
    exists and is theirs.

    Deliberately not `Document`: nothing on the guard path needs `content`, and a
    200 000-code-point field materialised on every request to all seven AI-edit
    endpoints answers a yes/no question at the cost of the largest column in the
    schema. See decisions/document-scope-guard-decision.md.

    Lives in its own module so `DocumentRepository` can name it in the signature
    of the bounded finder without importing the guard that consumes it.
    """

    id: UUID
    owner_id: UUID
