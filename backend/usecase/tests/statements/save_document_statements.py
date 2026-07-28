from uuid import UUID, uuid4

from document.document import Document
from document.save_document import SaveDocument
from document.title_update import TitleUpdate
from statements.document_fakes import (
    FakeClock,
    FakeDocumentRepository,
    FakeHtmlSanitizer,
    FakeUnitOfWork,
)

STORED_TITLE = "Привет Мир"
AUTOSAVE_CONTENT = "<p>черновик</p>"


# The three `type: ignore[arg-type]` below are the RED marker at the type level:
# `DocumentRepository.save_content_if_version_matches` and `SaveDocument.execute`
# still declare `title: str | None`, which per the ADR can no longer express intent.
# RED must not rewrite an existing port signature (that cascades into every
# adapter implementor) -- GREEN widens both to `TitleUpdate` and deletes these.
class SaveStatements:
    def __init__(self) -> None:
        self.repository = FakeDocumentRepository()
        self.sanitizer = FakeHtmlSanitizer()
        self.unit_of_work = FakeUnitOfWork()
        self.clock = FakeClock()
        self.usecase = SaveDocument(
            document_repository=self.repository,  # type: ignore[arg-type]
            html_sanitizer=self.sanitizer,
            clock=self.clock,
            unit_of_work=self.unit_of_work,
        )

    async def given_a_document(self, owner_id: UUID) -> Document:
        document = Document.create(
            owner_id=owner_id,
            document_type="эссе",
            idempotency_key=f"key-{uuid4()}",
            created_at=self.clock.now(),
        )
        await self.repository.save_new(document)
        return document


class SaveTitleStatements(SaveStatements):
    """Save-boundary title intent: what `execute` forwards across the port."""

    async def given_a_titled_document(self, owner_id: UUID) -> Document:
        document = await self.given_a_document(owner_id)
        await self.usecase.execute(
            document_id=document.id,
            owner_id=owner_id,
            content=AUTOSAVE_CONTENT,
            version=1,
            title=TitleUpdate.of(STORED_TITLE),  # type: ignore[arg-type]
        )
        return document

    async def when_autosaving_with_title(
        self, document: Document, owner_id: UUID, title: str
    ) -> None:
        await self.usecase.execute(
            document_id=document.id,
            owner_id=owner_id,
            content=AUTOSAVE_CONTENT,
            version=2,
            title=TitleUpdate.of(title),  # type: ignore[arg-type]
        )

    def assert_forwarded_title_update(self, expected: TitleUpdate) -> None:
        # The WHOLE recorded sequence, not just the last entry: the setup save
        # forwards `of(STORED_TITLE)` and the autosave forwards the value under
        # test, so pinning both also pins the call count -- a usecase that
        # mangled the setup title, or forwarded twice per call, would otherwise
        # still pass on a `[-1]` read.
        expected_sequence = [TitleUpdate.of(STORED_TITLE), expected]
        assert self.repository.title_updates == expected_sequence, (
            f"expected {expected_sequence!r} forwarded to the repository, "
            f"got {self.repository.title_updates!r}"
        )
