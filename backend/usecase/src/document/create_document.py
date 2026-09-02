from uuid import UUID

from document.document import Document
from document.document_creation import DocumentCreation, validate_idempotency_key
from document.document_creation_result import DocumentCreationResult
from document.document_repository import DocumentRepository
from document.document_type import DocumentType
from shared.clock import Clock
from shared.error_codes import ErrorCode
from shared.exceptions import ValidationException
from shared.unit_of_work import NullUnitOfWork, UnitOfWork


class CreateDocument:
    """Create an empty manual document. No LLM, no Generation, no polling."""

    INVALID_DOCUMENT_TYPE_MESSAGE = "Unsupported document type."
    CREATION_FAILED_MESSAGE = "The document could not be created."

    def __init__(
        self,
        document_repository: DocumentRepository,
        clock: Clock,
        unit_of_work: UnitOfWork | None = None,
    ) -> None:
        self._document_repository = document_repository
        self._clock = clock
        self._unit_of_work = unit_of_work or NullUnitOfWork()
        self._creation = DocumentCreation(document_repository, self._unit_of_work)

    async def execute(
        self, owner_id: UUID, document_type: str, idempotency_key: str
    ) -> DocumentCreationResult:
        self._validate(document_type, idempotency_key)
        document = Document.create(
            owner_id=owner_id,
            document_type=document_type,
            idempotency_key=idempotency_key,
            created_at=self._clock.now(),
        )
        return await self._creation.created_or_recovered(
            document, lambda: self._recover_replay(owner_id, idempotency_key)
        )

    def _validate(self, document_type: str, idempotency_key: str) -> None:
        # Both validated before the insert so a bad request never touches the DB.
        try:
            DocumentType(document_type)
        except ValueError as error:
            raise ValidationException(
                error_code=ErrorCode.INVALID_DOCUMENT_TYPE,
                message=self.INVALID_DOCUMENT_TYPE_MESSAGE,
            ) from error
        validate_idempotency_key(idempotency_key)

    async def _recover_replay(self, owner_id: UUID, idempotency_key: str) -> DocumentCreationResult:
        """The unique constraint fired: this owner already used the key.

        Why the rollback must come first: `DocumentCreation.created_or_recovered`.
        """
        await self._unit_of_work.rollback()
        existing = await self._document_repository.find_by_idempotency_key(
            owner_id, idempotency_key
        )
        if existing is None:
            # The row that won the race is not visible to us -- it was itself rolled
            # back between our insert failing and this read. Rare, and not something
            # to paper over: returning None here would 500 on a NoneType attribute
            # access with a traceback the client should never see.
            raise ValidationException(
                error_code=ErrorCode.DOCUMENT_CREATION_FAILED,
                message=self.CREATION_FAILED_MESSAGE,
            )
        return DocumentCreationResult(document=existing, is_replay=True)
