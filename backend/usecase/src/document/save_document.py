from typing import Optional
from uuid import UUID

from document.document import Document
from document.document_content import DocumentContent
from document.document_repository import DocumentRepository
from document.html_sanitizer import HtmlSanitizer
from shared.clock import Clock
from shared.exceptions import ConflictException, NotFoundException, ValidationException
from shared.unit_of_work import NullUnitOfWork, UnitOfWork

MIN_VERSION = 1


class SaveDocument:
    """Save the full editor content, guarded by the version token."""

    CONTENT_TOO_LONG_MESSAGE = "The content exceeds the maximum length of 200000 characters."
    INVALID_VERSION_MESSAGE = "The version must be a positive integer."

    def __init__(
        self,
        document_repository: DocumentRepository,
        html_sanitizer: HtmlSanitizer,
        clock: Clock,
        unit_of_work: Optional[UnitOfWork] = None,
    ) -> None:
        self.document_repository = document_repository
        self.html_sanitizer = html_sanitizer
        self.clock = clock
        self.unit_of_work = unit_of_work or NullUnitOfWork()

    async def execute(self, document_id: UUID, owner_id: UUID, content: str, version: int) -> Document:
        self._validate_version(version)
        # Length is checked here, before sanitizing: sanitizing first would make the
        # parser chew through an adversarial payload before we decline it, and the
        # cap is a contract about what the client sent, not about what survived
        # cleaning. DocumentContent caps the raw string, NFC-normalizes, then re-caps.
        normalized = self._validate_content(content)
        sanitized = self.html_sanitizer.sanitize(normalized)

        saved = await self.document_repository.save_content_if_version_matches(
            document_id=document_id,
            owner_id=owner_id,
            content=sanitized,
            expected_version=version,
            updated_at=self.clock.now(),
        )
        if saved is None:
            return await self._explain_miss(document_id, owner_id, sanitized, version)
        await self.unit_of_work.commit()
        return saved

    def _validate_version(self, version: int) -> None:
        # bool is an int subclass in Python, and `True == 1`, so a JSON `true` would
        # sail through a bare isinstance(version, int) check and act as version 1.
        if isinstance(version, bool) or not isinstance(version, int) or version < MIN_VERSION:
            raise ValidationException(
                error_code="INVALID_VERSION", message=self.INVALID_VERSION_MESSAGE
            )

    def _validate_content(self, content: str) -> str:
        try:
            return DocumentContent(content).value
        except ValueError as error:
            raise ValidationException(
                error_code="CONTENT_TOO_LONG", message=self.CONTENT_TOO_LONG_MESSAGE
            ) from error

    async def _explain_miss(
        self, document_id: UUID, owner_id: UUID, sanitized: str, version: int
    ) -> Document:
        """The CAS matched nothing. Work out which of the three reasons it was.

        The re-read is what lets scenario 6.2 answer 200: a client whose save
        already landed and retried would otherwise get a 409 and be sent into a
        refetch loop over a write that succeeded.

        The replay rule is deliberately narrow -- the stored content must equal
        ours AND the version must be exactly ours + 1. A `content -> other ->
        content` history therefore still conflicts, and (per the amended scenario
        6.7) two concurrent saves carrying *different* content cannot both pass:
        the loser's content will not match what landed.
        """
        current = await self.document_repository.find_by_id_and_owner(document_id, owner_id)
        if current is None:
            # Absent and foreign are one answer, always. A distinct response for
            # "exists but not yours" would confirm the id -- and a 409 here would
            # additionally confirm the version guess was right.
            raise NotFoundException(f"document {document_id} not found")
        if current.content == sanitized and current.version == version + 1:
            return current
        raise ConflictException(f"document {document_id} was modified concurrently")
