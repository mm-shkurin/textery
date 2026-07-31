import logging
from uuid import UUID

from document_edit.ai_edit_repository import AiEditRepository
from document_edit.ai_edit_scope import AiEditScope

from document.document_repository import DocumentRepository
from document.resolve_owned_document import REFUSAL_MESSAGE, resolve_owned_document
from shared.exceptions import NotFoundException

_LOGGER = logging.getLogger(__name__)

# One line for both causes, carrying no ids at all: the refusals are
# byte-identical to the caller, and everything that distinguishes them for the
# server lives in the structured fields, where an id can be asserted absent.
REFUSAL_LOG_MESSAGE = "ai edit guard refused the request"

# Step 1 and step 2 are told apart only here. A refusal at step 2 means the
# caller held a real edit id and asked for it under a document they do own --
# that is a probe, and without its own cause it looks like a typo'd document id.
DOCUMENT_SCOPE_REFUSAL_CAUSE = "document-scope-refused"
EDIT_SCOPE_REFUSAL_CAUSE = "edit-scope-refused"


async def resolve_owned_edit(
    document_repository: DocumentRepository,
    ai_edit_repository: AiEditRepository,
    *,
    document_id: UUID,
    edit_id: UUID,
    owner_id: UUID,
) -> AiEditScope:
    """Resolve an edit under a document the caller owns, or refuse as not found.

    The first statement of the three edit-id-carrying usecases (stream, state,
    cancel). Step 1 is `resolve_owned_document`; step 2 is the edit lookup. See
    19-ai-chat-editing/decisions/edit-scope-guard-decision.md.

    The three ids are keyword-only because they are three same-typed UUIDs in a
    row: a transposed `document_id`/`edit_id` at a call site type-checks, and
    resolves the wrong pair rather than failing -- which in a guard whose whole
    job is scoping is a silent authorization defect, not a bug that shows up in
    a stack trace.

    Only `NotFoundException` is caught around either step, never `Exception`: a
    broad catch would stamp a refusal record on a database outage, and a store
    that is down would then read as a probing campaign in our own logs while the
    caller got a 404 that hides the incident.
    """
    try:
        await resolve_owned_document(document_repository, document_id, owner_id)
    except NotFoundException:
        # No document id: step 1 refused precisely because the caller has no
        # proven claim to the one in the path.
        _LOGGER.info(
            REFUSAL_LOG_MESSAGE,
            extra={
                "refusal_cause": DOCUMENT_SCOPE_REFUSAL_CAUSE,
                "caller_id": str(owner_id),
            },
        )
        raise

    scope = await ai_edit_repository.find_scope_by_id_and_document(edit_id, document_id)
    if scope is None:
        # The document did resolve, so its id is the caller's own and is
        # recorded. The edit id is not: an unresolved id must not reach our logs.
        _LOGGER.info(
            REFUSAL_LOG_MESSAGE,
            extra={
                "refusal_cause": EDIT_SCOPE_REFUSAL_CAUSE,
                "caller_id": str(owner_id),
                "document_id": str(document_id),
            },
        )
        raise NotFoundException(REFUSAL_MESSAGE)
    return scope
