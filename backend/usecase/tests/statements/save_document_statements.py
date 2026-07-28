from uuid import UUID, uuid4

import pytest

from document.document import Document
from document.save_document import SaveDocument
from shared.exceptions import DomainException, ValidationException
from statements.arranged import arranged
from statements.document_fakes import (
    FakeClock,
    FakeDocumentRepository,
    FakeHtmlSanitizer,
    FakeUnitOfWork,
)

AUTOSAVE_CONTENT = "<p>черновик</p>"


class SaveStatements:
    def __init__(self) -> None:
        self.repository = FakeDocumentRepository()
        self.sanitizer = FakeHtmlSanitizer()
        self.unit_of_work = FakeUnitOfWork()
        self.clock = FakeClock()
        self.usecase = SaveDocument(
            document_repository=self.repository,
            html_sanitizer=self.sanitizer,
            clock=self.clock,
            unit_of_work=self.unit_of_work,
        )
        # Every save is recorded, not just the last: the replay case asserts that
        # a second identical submit produced the SAME version as the first, which
        # a `_saved`-overwriting field could not tell from a second advance.
        self._saves: list[Document] = []
        self._rejection: ValidationException | None = None

    @property
    def saved(self) -> Document:
        assert self._saves, "no save has been made yet -- call when_saving first"
        return self._saves[-1]

    async def given_a_document(self, owner_id: UUID) -> Document:
        document = Document.create(
            owner_id=owner_id,
            document_type="эссе",
            idempotency_key=f"key-{uuid4()}",
            created_at=self.clock.now(),
        )
        await self.repository.save_new(document)
        return document

    async def when_saving(
        self, document: Document, owner_id: UUID, content: str, version: int = 1
    ) -> None:
        self._saves.append(
            await self.usecase.execute(
                document_id=document.id, owner_id=owner_id, content=content, version=version
            )
        )

    async def when_saving_is_invalid(
        self, document: Document, owner_id: UUID, content: str, version: int = 1
    ) -> None:
        with pytest.raises(ValidationException) as error:
            await self.usecase.execute(
                document_id=document.id, owner_id=owner_id, content=content, version=version
            )
        self._rejection = error.value

    async def when_saving_is_refused(
        self,
        error_type: type[DomainException],
        document_id: UUID,
        owner_id: UUID,
        content: str,
        version: int = 1,
    ) -> None:
        """The refusals that carry no error code of their own -- absence, foreign
        ownership, and a stale version. Takes a raw `document_id` so the unknown-id
        case can present one that was never stored.
        """
        with pytest.raises(error_type):
            await self.usecase.execute(
                document_id=document_id, owner_id=owner_id, content=content, version=version
            )

    def assert_saved(self, content: str, version: int) -> None:
        assert self.saved.content == content, (
            f"expected the save to land {content!r}, got {self.saved.content!r}"
        )
        assert self.saved.version == version, "a successful save advances the version by one"

    def assert_saved_content(self, content: str, why: str) -> None:
        assert self.saved.content == content, why

    def assert_every_save_landed_on_version(self, version: int) -> None:
        versions = [save.version for save in self._saves]
        assert versions == [version] * len(versions), (
            f"no second version advance for a replay, expected every save at version "
            f"{version}, got {versions}"
        )

    def assert_sanitizer_saw(self, contents: list[str], why: str) -> None:
        assert self.sanitizer.sanitized == contents, why

    def assert_committed_once(self) -> None:
        assert self.unit_of_work.commit_call_count == 1, (
            f"expected exactly one commit, got {self.unit_of_work.commit_call_count}"
        )

    def assert_rejected_with(self, error_code: str) -> None:
        rejection = arranged(self._rejection, "_rejection")
        assert rejection.error_code == error_code, (
            f"expected error code {error_code}, got {rejection.error_code}"
        )

    async def assert_stored_content(
        self, document: Document, owner_id: UUID, content: str, why: str
    ) -> None:
        stored = await self._stored(document, owner_id)
        assert stored.content == content, why

    async def assert_response_matches_storage(self, document: Document, owner_id: UUID) -> None:
        stored = await self._stored(document, owner_id)
        assert stored.content == self.saved.content, "response and storage must not disagree"

    async def assert_nothing_was_written(self, document: Document, owner_id: UUID) -> None:
        stored = await self._stored(document, owner_id)
        assert stored.content == "", "an oversized save must not reach storage"
        assert stored.version == 1, "a rejected save must not advance the version"

    async def _stored(self, document: Document, owner_id: UUID) -> Document:
        return arranged(
            await self.repository.find_by_id_and_owner(document.id, owner_id),
            "the stored document",
        )
