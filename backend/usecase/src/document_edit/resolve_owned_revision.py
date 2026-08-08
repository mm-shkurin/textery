import logging
from uuid import UUID

from document_edit.document_revision_repository import DocumentRevisionRepository
from document_edit.refusal_log import DOCUMENT_SCOPE_REFUSAL_CAUSE, log_refusal
from document_edit.revision_scope import RevisionScope

from document.document_repository import DocumentRepository
from document.resolve_owned_document import REFUSAL_MESSAGE, resolve_owned_document
from shared.exceptions import NotFoundException

_LOGGER = logging.getLogger(__name__)

# One line for both causes, carrying no ids at all: the refusals are
# byte-identical to the caller, and everything that distinguishes them for the
# server lives in the structured fields, where an id can be asserted absent.
REFUSAL_LOG_MESSAGE = "revision guard refused the request"

# Step 2's cause. A cross-document probe against a real revision number must not
# read as an ordinary typo'd document id in the server's own records -- that is
# the one place the two are supposed to be distinguishable. Step 1's cause is
# shared with the edit guard and lives in `refusal_log`.
REVISION_SCOPE_REFUSAL_CAUSE = "revision-scope-refused"

# The storage range, written as the two bounds the `INTEGER` column actually
# holds rather than as `2**31 - 1`: the column type and this constant are the two
# halves of "the valid range is the storage range", and a computed bound agrees
# with whatever arithmetic is written next to it.
SMALLEST_STORABLE_REVISION_NUMBER = 1
LARGEST_STORABLE_REVISION_NUMBER = 2147483647


def _parse_in_range(revision_number: str) -> int | None:
    """The path value as a storable int, or `None` if it can never name a row.

    Python ints are unbounded and the column is not, so handing the raw value to
    the repository reaches the driver as a numeric-out-of-range error -- which
    this guard's deliberately narrow `except NotFoundException` correctly does
    not swallow, and which would surface as the 500 the restore contract forbids.
    Non-integer text is the same class of value by a different door: it cannot
    name a row either, and the route declares the parameter as `str` precisely so
    that FastAPI does not answer it 422 ahead of the Bearer dependency.
    """
    try:
        parsed = int(revision_number)
    except ValueError:
        return None
    if not SMALLEST_STORABLE_REVISION_NUMBER <= parsed <= LARGEST_STORABLE_REVISION_NUMBER:
        return None
    return parsed


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

    **The parse deliberately runs after step 1, not before it.** Both orderings
    answer the caller the same canonical 404, so nothing the caller can observe
    tells them apart -- but ordering the cheap check first makes the refusal
    record disappear: a caller asking for revision `0` under somebody else's
    document id would get the 404 having called neither repository and having
    emitted nothing, which is a way to probe document ids with the attribution
    channel switched off by choosing an out-of-range number. Step 1 is the
    authorization step, so it goes first and logs, and only then is the number
    the caller supplied inspected.

    Only `NotFoundException` is caught around either step, never `Exception`: a
    broad catch would stamp a refusal record on a database outage, and a store
    that is down would then read as a probing campaign in our own logs while the
    caller got a 404 that hides the incident.
    """
    try:
        await resolve_owned_document(document_repository, document_id, owner_id)
    except NotFoundException:
        log_refusal(_LOGGER, REFUSAL_LOG_MESSAGE, DOCUMENT_SCOPE_REFUSAL_CAUSE, owner_id)
        raise

    parsed_number = _parse_in_range(revision_number)
    if parsed_number is None:
        return _refuse_at_step_two(owner_id, document_id)

    scope = await revision_repository.find_scope_by_number_and_document(
        revision_number=parsed_number, document_id=document_id
    )
    if scope is None:
        return _refuse_at_step_two(owner_id, document_id)
    return scope


def _refuse_at_step_two(owner_id: UUID, document_id: UUID) -> RevisionScope:
    """Record the step-2 refusal and raise the canonical body.

    Declared as returning `RevisionScope` so the two call sites can `return` it
    and no reader has to know that control does not come back; it never does.

    The revision number is deliberately absent from the record: the document
    resolved, so its id is the caller's own, but a number the caller has not
    proven a claim to must not reach our logs. Both step-2 doors -- unparseable
    or out of range, and simply not there -- refuse through this one function, so
    a caller cannot tell from the body or the record which of them answered.
    """
    log_refusal(
        _LOGGER,
        REFUSAL_LOG_MESSAGE,
        REVISION_SCOPE_REFUSAL_CAUSE,
        owner_id,
        document_id=document_id,
    )
    raise NotFoundException(REFUSAL_MESSAGE)
