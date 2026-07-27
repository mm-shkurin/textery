import io

from docx import Document  # type: ignore[import-untyped]
from htmldocx import HtmlToDocx  # type: ignore[import-untyped]

from document.export_format import ExportFormat
from shared.clock import Clock

# The only author identity the exported file may carry. A neutral product
# constant, deliberately not the OS/process username python-docx would otherwise
# leave in docProps -- the group-07 metadata-redaction guard for the download.
_NEUTRAL_AUTHOR = "Textery"


class HtmlDocxRenderer:
    """DocumentRenderer port implementation for DOCX, pure-Python.

    Parses the stored, already-sanitized document HTML with `htmldocx` into a
    `python-docx` Document and returns the OOXML .docx bytes. No native binary
    and no network, so it adds nothing to fail-fast at boot beyond its pip deps
    and is SSRF-safe by construction (the parser resolves no external URLs).

    Metadata is redacted to neutral values: author identity is a fixed product
    constant rather than the machine account python-docx defaults to, and the
    created/modified instants come from the injected clock rather than the raw
    server wall clock -- so a downloaded file leaks no server identity or time.
    """

    def __init__(self, clock: Clock) -> None:
        self._clock = clock

    def render(self, content: str, export_format: ExportFormat) -> bytes:
        # export_format is DOCX here; the port stays uniform so this joins the
        # PDF renderer behind one signature (the dispatcher routes on the enum).
        document = Document()
        HtmlToDocx().add_html_to_document(content, document)

        now = self._clock.now()
        core = document.core_properties
        core.author = _NEUTRAL_AUTHOR
        core.last_modified_by = _NEUTRAL_AUTHOR
        core.created = now
        core.modified = now

        buffer = io.BytesIO()
        document.save(buffer)
        return buffer.getvalue()
