from typing import Any

import weasyprint  # type: ignore[import-untyped]

from document.export_format import ExportFormat


def _blocked_url_fetcher(url: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
    """Refuse every outbound fetch during a render.

    WeasyPrint's default fetcher would resolve `<img src="http://...">`,
    `@import`, remote `@font-face`, etc. -- an SSRF vector, since the document
    HTML is user-controlled. Plain document content triggers no fetch at all, so
    this never fires on the happy path; it exists to make an embedded external
    URL a hard failure rather than a silent outbound request (Security 4.1).
    """
    raise ValueError(f"external resource fetch blocked during export render: {url}")


class WeasyPrintPdfRenderer:
    """DocumentRenderer port implementation for PDF, backed by WeasyPrint.

    Renders the stored, already-sanitized document HTML to a PDF with the
    network turned off (see `_blocked_url_fetcher`). A separate DOCX renderer
    joins this behind the same port in Scenario 2.2; this class owns the PDF
    branch only.

    Lives in its own `rendering` adapter module rather than folded into an
    existing one: it is the first of two render adapters (PDF here, DOCX next),
    and it carries a heavy native dependency (Pango/cairo) that nothing else in
    the codebase shares.
    """

    def render(self, content: str, export_format: ExportFormat) -> bytes:
        # export_format is PDF here; the port stays uniform so the DOCX renderer
        # (Sc 2.2) can join behind the same signature. write_pdf(target=None)
        # returns the PDF as bytes.
        document = weasyprint.HTML(string=content, url_fetcher=_blocked_url_fetcher)
        return document.write_pdf()
