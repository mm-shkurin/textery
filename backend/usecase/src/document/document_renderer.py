from typing import Protocol

from document.export_format import ExportFormat


class DocumentRenderer(Protocol):
    """Port for rendering document content into a binary export (PDF/DOCX).

    A port rather than a domain rule because the domain has no dependencies and
    cannot import a rendering engine (WeasyPrint et al. live in an adapter). The
    method is unified over `ExportFormat` rather than split per format so a new
    target does not multiply the port surface -- the adapter dispatches on the
    enum. Synchronous by contract: the render runs in-process during the binary
    GET, there is no polling seam to await.
    """

    def render(self, content: str, export_format: ExportFormat) -> bytes: ...
