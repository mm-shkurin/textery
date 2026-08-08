from uuid import UUID

from document_edit.document_revision_repository import DocumentRevisionRepository
from document_edit.revision_scope import RevisionScope

from document.document_repository import DocumentRepository


async def resolve_owned_revision(
    document_repository: DocumentRepository,
    revision_repository: DocumentRevisionRepository,
    *,
    document_id: UUID,
    revision_number: str,
    owner_id: UUID,
) -> RevisionScope:
    """Resolve a revision under a document the caller owns, or refuse as not found.

    The first statement of the restore usecase. Step 1 is `resolve_owned_document`;
    step 2 is the revision lookup. A document the caller does not own never reaches
    step 2. See 19-ai-chat-editing/decisions/revision-scope-guard-decision.md.

    `revision_number` arrives as a `str` on purpose. The restore contract lists
    200/401/404/409/500 and no 422, and puts "non-integer" in the 404 body, so the
    route must not let FastAPI coerce the path parameter: coercion fires ahead of
    the Bearer dependency, and an unauthenticated caller would get 422 instead of
    401. Parsing and range-checking therefore happen here, in one place, before
    the repository is asked anything.
    """
    raise NotImplementedError()
