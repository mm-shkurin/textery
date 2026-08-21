"""A table the user built in the editor must be a VISIBLE table in the export.

Reported against the live stack 2026-08-20: «когда в ручном режиме добавляем
таблицу, то она не экспортируется в пдф и докс». The cells were exported — the PDF
carried all six text fragments — but nothing was drawn between them, because the
editor's table CSS lives in the frontend bundle and the stored document is a bare
fragment. A borderless grid is, to the reader, a table that did not export.

These tests assert the LINES, not the text. Text-only assertions passed throughout
the whole defect.
"""

import io
import re
import zipfile
import zlib
from datetime import UTC, datetime

import pytest

# Same collection guard as `test_html_docx_renderer`: htmldocx/python-docx are
# pure-Python but are not installed on a bare dev host, so the DOCX half is
# skipped there with a named reason rather than failing as though the renderer
# were broken. The PDF half guards WeasyPrint separately, inside its own helper,
# because that one needs native Pango/cairo and is absent in a different set of
# places.
pytest.importorskip("htmldocx")
pytest.importorskip("docx")

from document.export_format import ExportFormat  # noqa: E402
from rendering.html_docx_renderer import HtmlDocxRenderer  # noqa: E402

TABLE_HTML = (
    "<p>До таблицы</p>"
    "<table><tbody>"
    "<tr><th>Год</th><th>Событие</th></tr>"
    "<tr><td>1961</td><td>Первый полёт</td></tr>"
    "</tbody></table>"
    "<p>После таблицы</p>"
)


class _FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 8, 20, 12, 0, tzinfo=UTC)


def _document_xml(docx_bytes: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(docx_bytes)) as archive:
        return archive.read("word/document.xml").decode("utf-8")


def _rendered_xml(html: str = TABLE_HTML) -> str:
    return _document_xml(HtmlDocxRenderer(clock=_FixedClock()).render(html, ExportFormat.DOCX))


class TestDocxTableExport:
    def test_should_carry_the_table_as_a_real_docx_table(self):
        assert _rendered_xml().count("<w:tbl>") == 1, (
            "the table must survive as a table, not as loose text"
        )

    def test_should_apply_a_bordered_table_style(self):
        # The defect exactly: htmldocx's default style is None, which resolves to
        # "Normal Table" -- every cell present, not one line drawn. Asserting the
        # style reference is what separates a visible grid from an invisible one.
        assert 'w:val="TableGrid"' in _rendered_xml(), (
            "the table carries no bordered style, so it exports as an invisible grid"
        )

    def test_should_keep_every_cell_value(self):
        texts = re.findall(r"<w:t[^>]*>([^<]*)</w:t>", _rendered_xml())

        for expected in ("Год", "Событие", "1961", "Первый полёт"):
            assert expected in texts, f"{expected!r} is missing from the exported document"

    def test_should_keep_the_paragraphs_around_the_table(self):
        texts = re.findall(r"<w:t[^>]*>([^<]*)</w:t>", _rendered_xml())

        # A conversion that swallowed the surrounding prose while fixing the table
        # would trade one export bug for a worse one.
        assert "До таблицы" in texts
        assert "После таблицы" in texts


def _pdf_content_stream(pdf_bytes: bytes) -> bytes:
    streams = re.findall(rb"stream\r?\n(.*?)endstream", pdf_bytes, re.S)
    decoded = []
    for stream in streams:
        try:
            decoded.append(zlib.decompress(stream))
        except zlib.error:
            decoded.append(stream)
    return b"\n".join(decoded)


def _rectangle_ops(content: bytes) -> int:
    """How many rectangles the page draws.

    WeasyPrint paints a table's borders as filled rectangles, so this counts the
    LINES rather than the text. The regression was invisible to any text
    assertion: every cell's text was in the PDF the whole time.
    """
    return len(re.findall(rb"(?<![A-Za-z])re(?![A-Za-z])", content))


class TestPdfTableExport:
    """Runs only where WeasyPrint's native libraries exist (the backend image, CI).

    `importorskip` inside the fixture rather than a module-level import: on a dev
    host without Pango this suite is skipped with a named reason instead of
    failing as though the renderer were broken.
    """

    @staticmethod
    def _render(html: str) -> bytes:
        pytest.importorskip("weasyprint", reason="WeasyPrint needs native Pango/cairo")
        from rendering.weasyprint_pdf_renderer import WeasyPrintPdfRenderer

        return WeasyPrintPdfRenderer().render(html, ExportFormat.PDF)

    def test_should_draw_the_tables_borders(self):
        assert _rectangle_ops(_pdf_content_stream(self._render(TABLE_HTML))) > 0, (
            "the PDF draws no rectangles, so the table has no visible grid"
        )

    def test_should_draw_nothing_extra_for_a_document_with_no_table(self):
        # The non-vacuity gate for the assertion above: if a plain paragraph also
        # produced rectangles, the count would be measuring something other than
        # the table's borders and the test would pass against a broken renderer.
        assert _rectangle_ops(_pdf_content_stream(self._render("<p>Просто текст</p>"))) == 0

    def test_should_keep_the_cell_text(self):
        content = _pdf_content_stream(self._render(TABLE_HTML))

        # Six text-showing operations: the two paragraphs and the four cells.
        assert len(re.findall(rb"(?<![A-Za-z])(?:Tj|TJ)(?![A-Za-z])", content)) >= 6
