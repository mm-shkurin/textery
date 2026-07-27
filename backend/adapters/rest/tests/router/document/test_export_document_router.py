from uuid import uuid4

import pytest

from document.rendered_export import RenderedExport


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
        # The usecase now yields the rendered payload + its media type; the route
        # must hand those bytes back unchanged as a binary Response, never re-wrap
        # them in the DocumentResponseDto JSON placeholder.
        #
        # media_type is a DISTINCTIVE sentinel, not "application/pdf": the route
        # must THREAD RenderedExport.media_type into the response, and a green that
        # hardcodes "application/pdf" (ignoring the field) would pass a pdf-literal
        # assertion while silently mis-typing a future DOCX export. Asserting the
        # header echoes this sentinel forces the pass-through here rather than
        # leaking the bug into Scenario 2.2. The real "application/pdf" type on a
        # genuine render is pinned end to end by green-acceptance.
        rendered = RenderedExport(
            content=b"%PDF-1.7 fake pdf bytes", media_type="application/x-render-marker"
        )
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(return_value=rendered)

        async with export_client(usecase) as client:
            response = await client.get(f"/api/v1/documents/{uuid4()}/export?format=pdf")

        assert response.status_code == 200, f"got {response.status_code}: {response.text}"
        assert response.headers["content-type"] == "application/x-render-marker"
        assert response.content == b"%PDF-1.7 fake pdf bytes"
        assert response.headers["content-disposition"] == "attachment; filename=document.pdf"


@pytest.mark.skip(reason="RED: export route hardcodes filename=document.pdf, ignores rendered.filename")
class TestExportFilenameRfc5987:
    """Scenario 3.1: the download filename is derived from the title and RFC 5987
    percent-encoded so a Cyrillic title survives the Content-Disposition header.
    """

    async def test_should_encode_the_rendered_filename_per_rfc5987(
        self, mocker, export_client
    ):
        # The usecase derives the plain-unicode filename onto RenderedExport.filename
        # ("Привет Мир.pdf"). The route must stop hard-coding filename=document.pdf and
        # instead emit the RFC 5987 extended form: filename*=UTF-8''<percent-encoded>.
        # The expected header is literal-pinned (Cyrillic bytes + space encoded, the
        # dot and .pdf left literal) so nothing in the test re-derives the encoding --
        # a runtime encode() here would be a tautology that a hardcoded green passes.
        rendered = RenderedExport(
            content=b"%PDF-1.7 x",
            media_type="application/pdf",
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
