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

    @pytest.mark.skip(
        reason="RED: /export still wraps RenderedExport in DocumentResponseDto; "
        "binary Response is green-adapter rest (Scenario 2.1)"
    )
    async def test_should_stream_the_rendered_pdf_as_a_binary_attachment(
        self, mocker, export_client
    ):
        # The usecase now yields the rendered payload + its media type; the route
        # must hand those bytes back unchanged as a binary Response, never re-wrap
        # them in the DocumentResponseDto JSON placeholder.
        rendered = RenderedExport(
            content=b"%PDF-1.7 fake pdf bytes", media_type="application/pdf"
        )
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(return_value=rendered)

        async with export_client(usecase) as client:
            response = await client.get(f"/api/v1/documents/{uuid4()}/export?format=pdf")

        assert response.status_code == 200, f"got {response.status_code}: {response.text}"
        assert response.headers["content-type"] == "application/pdf"
        assert response.content == b"%PDF-1.7 fake pdf bytes"
        assert response.headers["content-disposition"] == "attachment; filename=document.pdf"
