from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class AiEditScope:
    """A bounded projection of an AI edit, for callers that only need to know it
    exists and belongs to the document in the path.

    Deliberately not the edit row: no instruction text, no diff, no generated
    content. Nothing on the guard path reads them, and a field no statement reads
    is a field that can only leak -- the guard runs on the three edit-id-carrying
    endpoints of every request.

    Lives in its own module so `AiEditRepository` can name it in the signature of
    the bounded finder without importing the guard that consumes it. See
    19-ai-chat-editing/decisions/edit-scope-guard-decision.md.
    """

    id: UUID
    document_id: UUID
