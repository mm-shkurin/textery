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
from statements.document_state import DocumentState

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
        self._refusal: DomainException | None = None
        # Field-by-field state as of the last `remember_stored_state`, so a
        # "nothing was written" claim can be checked against what was actually
        # there rather than against the two fields someone thought to name.
        self._snapshots: dict[UUID, DocumentState] = {}

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
        await self.remember_stored_state(document)
        return document

    async def remember_stored_state(self, document: Document) -> None:
        """Freeze the stored state so a later refusal can be checked against it."""
        stored = await self._stored(document)
        self._snapshots[document.id] = DocumentState.of(stored)

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
        with pytest.raises(error_type) as error:
            await self.usecase.execute(
                document_id=document_id, owner_id=owner_id, content=content, version=version
            )
        self._refusal = error.value

    def assert_saved(self, content: str, version: int) -> None:
        self.assert_saved_content(content, f"expected the save to land {content!r}")
        assert self.saved.version == version, (
            f"a successful save advances the version by one, expected {version}, "
            f"got {self.saved.version}"
        )
        assert self.saved.updated_at == self.clock.now(), (
            "a successful save stamps the clock's time, not the document's old one"
        )

    def assert_saved_content(self, content: str, why: str) -> None:
        assert self.saved.content == content, f"{why} (got {self.saved.content!r})"

    def assert_saves_landed_on_versions(self, versions: list[int]) -> None:
        # The EXPECTED sequence is passed in whole, never derived from the actual
        # one: `[version] * len(actual)` says only "all entries agree" and passes
        # vacuously on an empty list, so it could not tell a replay that produced
        # two saves at v2 from a usecase that saved once.
        actual = [save.version for save in self._saves]
        assert actual == versions, (
            f"expected the saves to land on versions {versions}, got {actual}"
        )

    def assert_refused_with_message(self, message: str) -> None:
        refusal = arranged(self._refusal, "_refusal")
        assert str(refusal) == message, (
            f"expected the refusal to read {message!r}, got {str(refusal)!r}"
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

    async def assert_stored_content(self, document: Document, content: str, why: str) -> None:
        stored = await self._stored(document)
        assert stored.content == content, f"{why} (got {stored.content!r})"

    async def assert_stored_title(self, document: Document, title: str | None) -> None:
        """The title as it actually sits in storage.

        Independent of the forwarded-intent assertion on purpose: the intent
        pins what `execute` ASKED for, this pins what the preserve-on-omit rule
        then did with it. It is also the tripwire for an omitted `title=` kwarg
        -- the fake's unpassed-argument sentinel carries a value, so a default
        that fires lands a visibly bogus title here.
        """
        stored = await self._stored(document)
        assert stored.title == title, (
            f"expected the stored title to be {title!r}, got {stored.title!r}"
        )

    async def assert_response_matches_storage(self, document: Document) -> None:
        stored = DocumentState.of(await self._stored(document))
        returned = DocumentState.of(self.saved)
        assert stored == returned, (
            f"response and storage must not disagree on ANY field: "
            f"stored {stored!r} vs returned {returned!r}"
        )

    async def assert_nothing_was_written(self, document: Document) -> None:
        expected = arranged(self._snapshots.get(document.id), "a remembered state")
        stored = DocumentState.of(await self._stored(document))
        assert stored == expected, (
            f"a refused save must leave EVERY field as it was: expected {expected!r}, "
            f"got {stored!r}"
        )

    def assert_no_title_intent_was_forwarded(self) -> None:
        assert self.repository.title_updates == [], (
            f"a save rejected before the port must not reach it at all, "
            f"got {self.repository.title_updates!r}"
        )

    async def _stored(self, document: Document) -> Document:
        """Reads back as the document's own owner -- the only owner these
        assertions ever meant. The foreign-owner refusals are covered by the
        `when_saving_is_refused` steps, which take their owner explicitly.
        """
        return arranged(
            await self.repository.find_by_id_and_owner(document.id, document.owner_id),
            "the stored document",
        )
