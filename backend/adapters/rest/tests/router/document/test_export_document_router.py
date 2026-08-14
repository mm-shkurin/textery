from uuid import uuid4

from document.export_format import ExportFormat
from document.rendered_export import RenderedExport
from dto.document.export_media_type import MEDIA_TYPE

DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class TestExportDocumentRoute:
    """Scenario 1.1: export of a non-existent document is refused with the sanctioned 404."""

    async def test_should_return_404_when_the_usecase_finds_nothing(self, mocker, export_client):
        # Absent and foreign both arrive as None from the owner-scoped usecase; the
        # route must translate that into the sanctioned NOT_FOUND body, never leak it.
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(return_value=None)

        async with export_client(usecase) as client:
            response = await client.get(f"/api/v1/documents/{uuid4()}/export")

        assert response.status_code == 404, f"got {response.status_code}: {response.text}"
        assert response.json() == {
            "error_code": "NOT_FOUND",
            "message": "The requested resource was not found.",
        }


class TestExportDocumentAsPdfResponse:
    """Scenario 2.1: the rendered PDF bytes stream back verbatim as a binary attachment."""

    async def test_should_stream_the_rendered_pdf_as_a_binary_attachment(
        self, mocker, export_client
    ):
        # The usecase yields the rendered payload and the FORMAT it rendered under;
        # naming the Content-Type is this layer's job. The route must hand the bytes
        # back unchanged as a binary Response, never re-wrap them in the
        # DocumentResponseDto JSON placeholder.
        #
        # The type is asserted per format rather than through a sentinel: with the
        # map on this side of the boundary, a route that hardcoded "application/pdf"
        # is caught by the DOCX case below instead of by a marker string.
        rendered = RenderedExport(
            content=b"%PDF-1.7 fake pdf bytes",
            export_format=ExportFormat.PDF,
            filename="document.pdf",
        )
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(return_value=rendered)

        async with export_client(usecase) as client:
            response = await client.get(f"/api/v1/documents/{uuid4()}/export?format=pdf")

        assert response.status_code == 200, f"got {response.status_code}: {response.text}"
        assert response.headers["content-type"] == "application/pdf"
        assert response.content == b"%PDF-1.7 fake pdf bytes"
        assert (
            response.headers["content-disposition"] == "attachment; filename*=UTF-8''document.pdf"
        )


class TestExportFilenameRfc5987:
    """Scenario 3.1: the download filename is derived from the title and RFC 5987
    percent-encoded so a Cyrillic title survives the Content-Disposition header.
    """

    async def test_should_encode_the_rendered_filename_per_rfc5987(self, mocker, export_client):
        # The usecase derives the plain-unicode filename onto RenderedExport.filename
        # ("Привет Мир.pdf"). The route must stop hard-coding filename=document.pdf and
        # instead emit the RFC 5987 extended form: filename*=UTF-8''<percent-encoded>.
        # The expected header is literal-pinned (Cyrillic bytes + space encoded, the
        # dot and .pdf left literal) so nothing in the test re-derives the encoding --
        # a runtime encode() here would be a tautology that a hardcoded green passes.
        rendered = RenderedExport(
            content=b"%PDF-1.7 x",
            export_format=ExportFormat.PDF,
            filename="Привет Мир.pdf",
        )
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(return_value=rendered)

        async with export_client(usecase) as client:
            response = await client.get(f"/api/v1/documents/{uuid4()}/export")

        assert response.status_code == 200, f"got {response.status_code}: {response.text}"
        assert response.headers["content-disposition"] == (
            "attachment; filename*=UTF-8''"
            "%D0%9F%D1%80%D0%B8%D0%B2%D0%B5%D1%82%20%D0%9C%D0%B8%D1%80.pdf"
        )


class TestExportContentTypePerFormat:
    """Scenario 2.2: the Content-Type follows the format, and every format has one.

    The map moved here from the usecase, and so did the exhaustiveness guard that
    used to live beside it: a format added without a media type must fail loudly
    at this layer rather than KeyError into a 500 the first time someone asks for
    it.
    """

    async def test_should_type_a_docx_export_as_a_word_document(self, mocker, export_client):
        rendered = RenderedExport(
            content=b"PK\x03\x04 fake docx bytes",
            export_format=ExportFormat.DOCX,
            filename="document.docx",
        )
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(return_value=rendered)

        async with export_client(usecase) as client:
            response = await client.get(f"/api/v1/documents/{uuid4()}/export?format=docx")

        assert response.status_code == 200, f"got {response.status_code}: {response.text}"
        assert response.headers["content-type"] == DOCX_MEDIA_TYPE
        assert response.content == b"PK\x03\x04 fake docx bytes"

    def test_every_export_format_resolves_to_a_media_type(self):
        unmapped = set(ExportFormat) - set(MEDIA_TYPE)

        assert unmapped == set(), (
            f"every ExportFormat member must map to a media type; unmapped: {unmapped}"
        )
