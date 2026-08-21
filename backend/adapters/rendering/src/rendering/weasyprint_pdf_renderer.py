from typing import Any

import weasyprint

from document.export_format import ExportFormat
from rendering.export_styles import EXPORT_CSS


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
        # The stylesheet is passed as an OBJECT, not embedded in the HTML string as
        # a `<style>` block. Embedding would mean concatenating our CSS onto
        # user-controlled markup, where an unclosed construct in the document could
        # swallow it -- and it would also put a `<style>` tag into content the
        # sanitizer strips `<style>` from, which is a contradiction the next reader
        # would have to resolve. `stylesheets=` keeps the two separate all the way
        # into the rendering engine.
        #
        # `url_fetcher` still refuses every outbound request: a local CSS object is
        # not a fetch, so the SSRF guard is untouched by this.
        return document.write_pdf(stylesheets=[weasyprint.CSS(string=EXPORT_CSS)])
