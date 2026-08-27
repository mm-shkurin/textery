"""The two steps both document-creation usecases perform identically.

`CreateDocument` (an empty manual document) and `CreateDocumentFromGeneration` (a
finished generation turned editable) are separate top-level usecases and neither
calls the other — usecases do not compose (`.claude/rules/coding-rules.md`). What
they share is extracted here instead: a module of plain functions, not a usecase,
with no `execute` and nothing wired into it.

Both steps had been written out twice, and each is the kind of duplication that
does not stay identical. The refusal message is part of the API contract, so a
reword on one route and not the other is a contract change nobody ordered; and the
insert dance below is subtle enough that its explanation was carried in two
docstrings that had already drifted apart in wording.
"""

from collections.abc import Awaitable, Callable

from document.document import Document
from document.document_creation_result import DocumentCreationResult
from document.document_repository import DocumentRepository
from document.idempotency_key import IdempotencyKey
from shared.error_codes import ErrorCode
from shared.exceptions import ConflictException, ValidationException
from shared.unit_of_work import UnitOfWork

INVALID_IDEMPOTENCY_KEY_MESSAGE = "The Idempotency-Key header must be 1 to 128 characters."


def validate_idempotency_key(idempotency_key: str) -> None:
    """Refuse a malformed key in this API's envelope, before anything touches the DB.

    The value object owns the RULE and raises `ValueError`; this owns the
    `error_code` and message the route answers with. Both creation routes answer
    the same pair, because to a client they are the same refusal about the same
    header.
    """
    try:
        IdempotencyKey(idempotency_key)
    except ValueError as error:
        raise ValidationException(
            error_code=ErrorCode.INVALID_IDEMPOTENCY_KEY,
            message=INVALID_IDEMPOTENCY_KEY_MESSAGE,
        ) from error


class DocumentCreation:
    """The repository and the transaction, which only ever travel together.

    A small collaborator rather than two parameters on a function: both creation
    usecases hold exactly these two and passed both at every call, which is the
    signal to bind them once. Not a usecase — it has no `execute`, is constructed
    by the usecases themselves rather than wired, and decides nothing about which
    document gets built.
    """

    def __init__(self, document_repository: DocumentRepository, unit_of_work: UnitOfWork) -> None:
        self._document_repository = document_repository
        self._unit_of_work = unit_of_work

    async def created_or_recovered(
        self,
        document: Document,
        recover: Callable[[], Awaitable[DocumentCreationResult]],
    ) -> DocumentCreationResult:
        """Insert the document; on a unique-constraint conflict, hand over to `recover`.

        Returns the whole result rather than a "did it conflict?" flag, so a caller
        is one `return` and cannot get the not-a-replay answer wrong.

        Which constraint fired, and what to answer with, is the caller's: the two
        creation routes recover by different reads and refuse with different codes.
        What is shared is the ORDER, and the order is the subtle part.

        **The rollback inside a recovery is load-bearing, not tidy-up**, and this is
        the one place it is explained — both `recover` implementations point here
        rather than restating it, because three wordings of one rule is how two of
        them stop being true. After an
        IntegrityError the session is poisoned and the very next query raises
        `PendingRollbackError`, so a recovery that re-reads without rolling back
        first turns a legitimate replay into a 500. `RegisterUser` never hit this
        because it rolls back and *aborts*; here we roll back and then *read*.

        The commit happens only on the non-conflicting path. A recovery has nothing
        to write — it answers with a row somebody else already committed.
        """
        try:
            await self._document_repository.save_new(document)
        except ConflictException:
            return await recover()
        await self._unit_of_work.commit()
        return DocumentCreationResult(document=document, is_replay=False)
