import pytest

from document.export_format import ExportFormat

# No importorskip here: FormatDispatchingRenderer receives the PDF and DOCX
# renderers by injection (the composition root wires the real WeasyPrint/htmldocx
# ones), so this suite drives it with in-memory fakes and needs no native lib.
# The production import is deferred into each test method so collection stays
# clean while the adapter does not yet exist -- the class-level skip disables the
# methods, and green removes the marker.

# A sentinel that is deliberately not a mapped ExportFormat. Dispatching on it
# must raise loudly rather than fall through a bare dict lookup that could return
# the wrong renderer's bytes.
_UNKNOWN_FORMAT = object()


class FakeRenderer:
    def __init__(self, output: bytes) -> None:
        self._output = output
        self.calls: list[tuple[str, object]] = []

    def render(self, content: str, export_format) -> bytes:
        self.calls.append((content, export_format))
        return self._output


class TestFormatDispatchingRenderer:
    def test_should_route_docx_to_the_docx_renderer(self):
        from rendering.format_dispatching_renderer import FormatDispatchingRenderer

        pdf = FakeRenderer(b"PDF-BYTES")
        docx = FakeRenderer(b"DOCX-BYTES")
        renderer = FormatDispatchingRenderer(pdf_renderer=pdf, docx_renderer=docx)

        result = renderer.render("<p>hi</p>", ExportFormat.DOCX)

        assert result == b"DOCX-BYTES"
        assert docx.calls == [("<p>hi</p>", ExportFormat.DOCX)]
        assert pdf.calls == []

    def test_should_route_pdf_to_the_pdf_renderer(self):
        from rendering.format_dispatching_renderer import FormatDispatchingRenderer

        pdf = FakeRenderer(b"PDF-BYTES")
        docx = FakeRenderer(b"DOCX-BYTES")
        renderer = FormatDispatchingRenderer(pdf_renderer=pdf, docx_renderer=docx)

        result = renderer.render("<p>hi</p>", ExportFormat.PDF)

        assert result == b"PDF-BYTES"
        assert pdf.calls == [("<p>hi</p>", ExportFormat.PDF)]
        assert docx.calls == []

    def test_should_raise_loudly_on_an_unmapped_format(self):
        from rendering.format_dispatching_renderer import FormatDispatchingRenderer

        pdf = FakeRenderer(b"PDF-BYTES")
        docx = FakeRenderer(b"DOCX-BYTES")
        renderer = FormatDispatchingRenderer(pdf_renderer=pdf, docx_renderer=docx)

        with pytest.raises(ValueError) as error:
            renderer.render("<p>hi</p>", _UNKNOWN_FORMAT)

        assert "format" in str(error.value).lower()
        assert pdf.calls == []
        assert docx.calls == []
