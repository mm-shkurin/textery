from uuid import UUID

from document.document import Document
from document.document_creation_result import DocumentCreationResult
from document.document_repository import DocumentRepository
from document.document_type import DocumentType
from document.idempotency_key import IdempotencyKey
from shared.clock import Clock
from shared.exceptions import ConflictException, ValidationException
from shared.unit_of_work import NullUnitOfWork, UnitOfWork


class CreateDocument:
    """Create an empty manual document. No LLM, no Generation, no polling."""

    INVALID_DOCUMENT_TYPE_MESSAGE = "Unsupported document type."
    INVALID_IDEMPOTENCY_KEY_MESSAGE = "The Idempotency-Key header must be 1 to 128 characters."
    CREATION_FAILED_MESSAGE = "The document could not be created."

    def __init__(
        self,
        document_repository: DocumentRepository,
        clock: Clock,
        unit_of_work: UnitOfWork | None = None,
    ) -> None:
        self.document_repository = document_repository
        self.clock = clock
        self.unit_of_work = unit_of_work or NullUnitOfWork()

    async def execute(
        self, owner_id: UUID, document_type: str, idempotency_key: str
    ) -> DocumentCreationResult:
        self._validate(document_type, idempotency_key)
        document = Document.create(
            owner_id=owner_id,
            document_type=document_type,
            idempotency_key=idempotency_key,
            created_at=self.clock.now(),
        )
        try:
            await self.document_repository.save_new(document)
        except ConflictException:
            return await self._recover_replay(owner_id, idempotency_key)
        await self.unit_of_work.commit()
        return DocumentCreationResult(document=document, is_replay=False)

    def _validate(self, document_type: str, idempotency_key: str) -> None:
        # Both validated before the insert so a bad request never touches the DB.
        try:
            DocumentType(document_type)
        except ValueError as error:
            raise ValidationException(
                error_code="INVALID_DOCUMENT_TYPE", message=self.INVALID_DOCUMENT_TYPE_MESSAGE
            ) from error
        try:
            IdempotencyKey(idempotency_key)
        except ValueError as error:
            raise ValidationException(
                error_code="INVALID_IDEMPOTENCY_KEY", message=self.INVALID_IDEMPOTENCY_KEY_MESSAGE
            ) from error

    async def _recover_replay(self, owner_id: UUID, idempotency_key: str) -> DocumentCreationResult:
        """The unique constraint fired: this owner already used the key.

        The rollback is load-bearing, not tidy-up. After an IntegrityError the
        session is poisoned and the very next query raises PendingRollbackError --
        so without it the re-read below fails and a legitimate retry 500s.
        RegisterUser never hit this because it rolls back and *aborts*; here we
        roll back and then *read*.
        """
        await self.unit_of_work.rollback()
        existing = await self.document_repository.find_by_idempotency_key(owner_id, idempotency_key)
        if existing is None:
            # The row that won the race is not visible to us -- it was itself rolled
            # back between our insert failing and this read. Rare, and not something
            # to paper over: returning None here would 500 on a NoneType attribute
            # access with a traceback the client should never see.
            raise ValidationException(
                error_code="DOCUMENT_CREATION_FAILED", message=self.CREATION_FAILED_MESSAGE
            )
        return DocumentCreationResult(document=existing, is_replay=True)
