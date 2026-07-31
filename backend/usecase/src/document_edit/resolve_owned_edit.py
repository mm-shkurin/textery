from uuid import UUID

from document_edit.ai_edit_repository import AiEditRepository
from document_edit.ai_edit_scope import AiEditScope

from document.document_repository import DocumentRepository


async def resolve_owned_edit(
    document_repository: DocumentRepository,
    ai_edit_repository: AiEditRepository,
    document_id: UUID,
    edit_id: UUID,
    owner_id: UUID,
) -> AiEditScope:
    """Resolve an edit under a document the caller owns, or refuse as not found.

    The first statement of the three edit-id-carrying usecases (stream, state,
    cancel). Step 1 is `resolve_owned_document`; step 2 is the edit lookup. See
    19-ai-chat-editing/decisions/edit-scope-guard-decision.md.
    """
    raise NotImplementedError()
