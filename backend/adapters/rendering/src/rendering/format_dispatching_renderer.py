from document.document_renderer import DocumentRenderer
from document.export_format import ExportFormat


class FormatDispatchingRenderer:
    """DocumentRenderer port implementation that routes by export format.

    The port is unified over `ExportFormat`, but each target needs its own
    engine (WeasyPrint for PDF, htmldocx/python-docx for DOCX). This adapter
    holds one renderer per format and dispatches `render` on the enum, so a new
    target adds a map entry rather than widening the port surface.

    An unmapped member raises loudly and calls neither renderer -- a bare dict
    lookup that fell through could hand back the wrong format's bytes under a
    correct-looking media type, so the failure is made explicit instead.
    """

    def __init__(self, pdf_renderer: DocumentRenderer, docx_renderer: DocumentRenderer) -> None:
        self._renderers: dict[ExportFormat, DocumentRenderer] = {
            ExportFormat.PDF: pdf_renderer,
            ExportFormat.DOCX: docx_renderer,
        }

    def render(self, content: str, export_format: ExportFormat) -> bytes:
        renderer = self._renderers.get(export_format)
        if renderer is None:
            raise ValueError(f"unsupported export format: {export_format!r}")
        return renderer.render(content, export_format)
