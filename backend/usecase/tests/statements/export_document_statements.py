from uuid import UUID, uuid4

import pytest

from document.export_document import _MEDIA_TYPE, ExportDocument
from document.export_format import ExportFormat
from document.get_document import GetDocument
from document.rendered_export import RenderedExport
from shared.exceptions import ValidationException
from statements.arranged import arranged
from statements.document_fakes import FakeDocumentRepository, stored_document

FAKE_RENDERED_PDF = b"%PDF-1.7\nfake-rendered-bytes"


class FakeDocumentRenderer:
    """Records every render call and returns fixed sentinel bytes.

    The sentinel matters: bytes a plain document could never carry. A usecase
    that skipped the render step, or echoed the stored content back instead of
    rendering it, could not produce these exact bytes -- so the happy-path
    assertion is a real proof the STORED content was fed through the renderer,
    not a tautology. `calls` records `(content, export_format)` so the test can
    pin that the usecase rendered the stored content under the parsed format,
    and that a refused request (absent doc / bad format) never reaches render.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, ExportFormat]] = []

    def render(self, content: str, export_format: ExportFormat) -> bytes:
        self.calls.append((content, export_format))
        return FAKE_RENDERED_PDF


class ExportStatements:
    """Fetch-and-render side of exporting, driven through the usecase boundary.

    One owner is fixed at construction, so every step speaks about "the caller's
    own" document without threading an id through the test. The repository starts
    empty: `given_no_stored_document` only invents an id, which is what makes the
    invalid-format steps prove the guard fired ahead of the fetch rather than the
    fetch merely missing.
    """

    def __init__(self) -> None:
        self.repository = FakeDocumentRepository()
        self.renderer = FakeDocumentRenderer()
        # Same RED marker as the one in `save_document_statements`: the shared fake
        # already takes a `TitleUpdate`, while `DocumentRepository` still declares
        # `title: str | None`. Export never passes a title, so this is purely the
        # port's pending widening surfacing here -- GREEN deletes both markers.
        self.usecase = ExportDocument(
            document_repository=self.repository,  # type: ignore[arg-type]
            document_renderer=self.renderer,
        )
        # The read-back after the export goes through GetDocument rather than the
        # repository port: state is verified through a usecase, never by querying
        # storage from a Statements class. GetDocument is a pure owner-scoped fetch,
        # so it adds no behaviour that could mask an export-side mutation.
        self.get_usecase = GetDocument(
            document_repository=self.repository,  # type: ignore[arg-type]
        )
        self._owner_id = uuid4()
        self._document_id: UUID | None = None
        self._result: RenderedExport | None = None
        self._error: ValidationException | None = None
        self._document_before_export: dict | None = None

    @property
    def document_id(self) -> UUID:
        return arranged(self._document_id, "_document_id")

    @property
    def result(self) -> RenderedExport:
        return arranged(self._result, "_result")

    def given_no_stored_document(self) -> None:
        self._document_id = uuid4()

    async def given_a_stored_document(self, content: str = "", title: str | None = None) -> None:
        document = stored_document(self._owner_id, content=content, title=title)
        await self.repository.save_new(document)
        self._document_id = document.id
        # Snapshot EVERY field by value before the export runs. `Document` is a plain
        # mutable class and the fake hands back the same instance it stored, so a copy
        # taken here is the only thing that can still tell "unchanged" from "mutated
        # in place" afterwards.
        self._document_before_export = dict(document.__dict__)

    async def when_exporting(self, export_format: str | None) -> None:
        self._result = await self.usecase.execute(
            document_id=self.document_id, owner_id=self._owner_id, format=export_format
        )

    async def when_exporting_is_refused(self, export_format: str | None) -> None:
        with pytest.raises(ValidationException) as error:
            await self.usecase.execute(
                document_id=self.document_id, owner_id=self._owner_id, format=export_format
            )
        self._error = error.value

    def assert_export_withheld(self) -> None:
        assert self._result is None, (
            f"expected None for a document the caller cannot see, got {self._result!r}"
        )

    def assert_nothing_was_rendered(self) -> None:
        assert self.renderer.calls == [], (
            f"a refused request must never reach the render step, got {self.renderer.calls!r}"
        )

    def assert_invalid_format_reported(self, bad_format: str | None) -> None:
        error = arranged(self._error, "_error")
        assert error.error_code == "INVALID_FORMAT", (
            f"expected INVALID_FORMAT for {bad_format!r}, got {error.error_code}"
        )
        assert error.message == "The format must be pdf or docx.", (
            f"unexpected message for {bad_format!r}: {error.message}"
        )

    def assert_rendered_stored_content(self, content: str, export_format: ExportFormat) -> None:
        assert self.renderer.calls == [(content, export_format)], (
            f"the usecase must render the STORED content under the parsed "
            f"{export_format!r}, got {self.renderer.calls!r}"
        )

    def assert_export_is(self, media_type: str, filename: str) -> None:
        expected = RenderedExport(
            content=FAKE_RENDERED_PDF, media_type=media_type, filename=filename
        )
        assert self.result == expected, f"expected {expected!r}, got {self.result!r}"

    async def assert_stored_document_unchanged(self, expected_title: str | None) -> None:
        """Re-reads the document through GetDocument and pins EVERY field.

        `assert_export_is` pins only the DERIVED name, which leaves open WHERE
        the strip lands: a green written as `document.title = (document.title or
        "").strip()` before the derivation produces the very same filename and turns
        every param green. It is invisible because `Document` is a plain mutable
        class and the fake hands back the SAME instance it stored, so the mutation
        never surfaces in the export result. The ADR forbids exactly that: stripping
        affects the filename only, the stored title is never rewritten -- and since
        an ordinary autosave is a read-modify-write, a read-path strip becomes a
        persisted wipe.

        Two assertions, and both are load-bearing. The whole-entity comparison
        against the pre-export snapshot catches an in-place mutation of ANY field
        (content, version, updated_at), not just the title -- exporting is a read.
        The explicit title pin catches what the snapshot cannot: a strip in
        `Document`'s constructor would already have stripped the snapshot itself,
        so only comparing against the RAW parametrized title still fails. (A strip
        in `DocumentModel.to_domain` is out of reach at this layer -- the fake has
        no mapper -- and is pinned by the h2 adapter tests instead.)
        """
        stored = await self.get_usecase.execute(self.document_id, self._owner_id)
        assert stored is not None, "the exported document must still be readable after export"
        assert stored.title == expected_title, (
            f"exporting must leave the stored title untouched: expected "
            f"{expected_title!r}, got {stored.title!r}"
        )
        before = arranged(self._document_before_export, "_document_before_export")
        assert dict(stored.__dict__) == before, (
            f"exporting must not mutate ANY stored field: expected {before!r}, "
            f"got {stored.__dict__!r}"
        )

    def assert_every_export_format_resolves_to_a_media_type(self) -> None:
        """Reaches into the usecase's private `_MEDIA_TYPE` deliberately.

        The map has no public accessor -- exposing one would widen the usecase's
        API for a test's convenience. Keeping the private read here, behind a
        named step, is what lets the test class stay pure DSL.
        """
        unmapped = set(ExportFormat) - set(_MEDIA_TYPE)
        assert unmapped == set(), (
            f"every ExportFormat member must map to a media type; unmapped: {unmapped}"
        )
