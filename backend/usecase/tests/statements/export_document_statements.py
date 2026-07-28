from uuid import UUID, uuid4

import pytest

from document.export_document import ExportDocument
from document.export_format import ExportFormat
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
        self._owner_id = uuid4()
        self._document_id: UUID | None = None
        self._result: RenderedExport | None = None
        self._error: ValidationException | None = None

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

    def assert_filename_is(self, expected_filename: str, title: str | None) -> None:
        assert self.result.filename == expected_filename, (
            f"expected filename {expected_filename!r} for title {title!r}, "
            f"got {self.result.filename!r}"
        )
