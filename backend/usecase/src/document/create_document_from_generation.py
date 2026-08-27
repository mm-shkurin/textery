from uuid import UUID

from document.document import Document
from document.document_content import MAX_CONTENT_LENGTH, DocumentContent
from document.document_creation import DocumentCreation, validate_idempotency_key
from document.document_creation_result import DocumentCreationResult
from document.document_repository import DocumentRepository
from document.generated_title import derive_generated_title
from document.html_sanitizer import HtmlSanitizer
from document.markdown_converter import MarkdownConverter
from generation.generation import COMPLETED_STATUS, Generation
from generation.generation_storage import GenerationStorage
from shared.clock import Clock
from shared.error_codes import ErrorCode
from shared.exceptions import NotFoundException, ValidationException
from shared.unit_of_work import NullUnitOfWork, UnitOfWork


class CreateDocumentFromGeneration:
    """Turn a completed generation into the editable document the user edits.

    The whole auto path depends on this: the editor opens on the text the user
    just watched being written, and until that text is a Document it has no id to
    save against, no version to guard a save with, and nothing to export.

    Reads GenerationStorage directly rather than calling GetGeneration. Usecases
    do not compose (see .claude/rules/coding-rules.md) -- a usecase is a top-level
    entry point, and chaining one into another would hide this operation's real
    call graph and drag another operation's transactional boundary in with it.
    A port is the shared thing; the port is what gets injected.

    The Generation is left UNCHANGED. It stays the audit record of what the model
    produced, and the Document becomes the thing that is edited -- so a later
    question about whether the user or the model wrote a paragraph is still
    answerable.
    """

    NOT_COMPLETED_MESSAGE = "This generation is not finished yet and cannot become a document."
    KEY_REUSED_MESSAGE = "This Idempotency-Key already belongs to a different document."
    CONTENT_TOO_LONG_MESSAGE = (
        f"The generated text exceeds the maximum length of {MAX_CONTENT_LENGTH} characters."
    )
    CREATION_FAILED_MESSAGE = "The document could not be created."

    def __init__(
        self,
        document_repository: DocumentRepository,
        generation_storage: GenerationStorage,
        markdown_converter: MarkdownConverter,
        html_sanitizer: HtmlSanitizer,
        clock: Clock,
        unit_of_work: UnitOfWork | None = None,
    ) -> None:
        self._document_repository = document_repository
        self._generation_storage = generation_storage
        self._markdown_converter = markdown_converter
        self._html_sanitizer = html_sanitizer
        self._clock = clock
        self._unit_of_work = unit_of_work or NullUnitOfWork()
        self._creation = DocumentCreation(document_repository, self._unit_of_work)

    async def execute(
        self, owner_id: UUID, generation_id: UUID, idempotency_key: str
    ) -> DocumentCreationResult:
        validate_idempotency_key(idempotency_key)
        generation, generated_markdown = await self._load_completed_generation(
            owner_id, generation_id
        )
        document = Document.create_from_generation(
            owner_id=owner_id,
            document_type=generation.document_type,
            generation_id=generation_id,
            content=self._convert(generated_markdown),
            title=derive_generated_title(generation.topic),
            idempotency_key=idempotency_key,
            created_at=self._clock.now(),
        )
        return await self._creation.created_or_recovered(
            document, lambda: self._recover_existing(owner_id, generation_id)
        )

    async def _load_completed_generation(
        self, owner_id: UUID, generation_id: UUID
    ) -> tuple[Generation, str]:
        """The caller's own generation and its text, refusing anything not ready.

        Absent and foreign are ONE answer, and the storage read makes it
        structural: `get_by_id_and_owner` filters on owner in SQL, so a foreign
        generation returns None here exactly as a missing one does. A 403 would
        confirm the id exists to someone who guessed it.

        Returns the content as a separate `str` rather than leaving the caller to
        read `generation.content`, which is `str | None`. The emptiness check
        below is what makes it a `str`, and returning it is what carries that
        proof to the caller: the text cannot be reached except through the method
        that established it is there. Re-reading the attribute afterwards would
        put the guarantee back on a convention nothing enforces.
        """
        generation = await self._generation_storage.get_by_id_and_owner(generation_id, owner_id)
        if generation is None:
            raise NotFoundException(f"generation {generation_id} not found")
        # Fails CLOSED on anything that is not the one status we can convert --
        # pending, in_progress, failed, and any status a later story adds. An
        # allowlist rather than a `!= FAILED` denylist: the new status is the one
        # nobody remembers to handle, and converting a half-written generation
        # would hand the user a truncated document as if it were finished.
        if generation.status != COMPLETED_STATUS or not generation.content:
            raise ValidationException(
                error_code=ErrorCode.GENERATION_NOT_COMPLETED, message=self.NOT_COMPLETED_MESSAGE
            )
        return generation, generation.content

    def _convert(self, generated_markdown: str) -> str:
        """Markdown from the model to storable, editor-shaped HTML.

        Order is load-bearing: convert, THEN sanitize, THEN cap.

        Sanitizing after conversion is what makes the sanitizer the single control
        point for stored markup -- markdown permits raw embedded HTML, so a
        `<script>` in the model's answer survives the parser by design and must
        meet the same allowlist a client-submitted PUT does.

        The cap is measured last because both earlier steps change the length:
        conversion adds tags and sanitization escapes bare angle brackets. Capping
        the markdown would let a document just under the limit grow past it and
        fail at the column instead of at the boundary.
        """
        html = self._html_sanitizer.sanitize(self._markdown_converter.to_html(generated_markdown))
        try:
            return DocumentContent(html).value
        except ValueError as error:
            raise ValidationException(
                error_code=ErrorCode.CONVERTED_CONTENT_TOO_LONG,
                message=self.CONTENT_TOO_LONG_MESSAGE,
            ) from error

    async def _recover_existing(
        self, owner_id: UUID, generation_id: UUID
    ) -> DocumentCreationResult:
        """A unique constraint fired. Answer with the document that won.

        Which constraint it was is decided by what this read finds, rather than by
        parsing a driver-specific constraint name off the error:

          - a document for this generation exists -> the conversion already
            happened (a replay, or a concurrent request that beat us). Returning it
            is the idempotent answer, and it is the SAME document, never a second
            one -- which is the point of the constraint.
          - nothing found -> the Idempotency-Key collided with an unrelated
            document. Silently returning that document would hand the caller
            somebody else's text under their own generation's name, so it is
            refused instead.

        The rollback is load-bearing, not tidy-up: after an IntegrityError the
        session is poisoned and the next query raises PendingRollbackError, so
        without it this read fails and a legitimate replay 500s.
        """
        await self._unit_of_work.rollback()
        existing = await self._document_repository.find_by_generation_id(owner_id, generation_id)
        if existing is not None:
            return DocumentCreationResult(document=existing, is_replay=True)
        raise ValidationException(
            error_code=ErrorCode.IDEMPOTENCY_KEY_REUSED, message=self.KEY_REUSED_MESSAGE
        )
