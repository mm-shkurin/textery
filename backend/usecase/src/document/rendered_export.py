from dataclasses import dataclass


@dataclass(frozen=True)
class RenderedExport:
    """What ExportDocument returns on the found path.

    A bare `bytes` cannot tell the router which Content-Type to stamp, so the
    rendered payload and its media type travel together. Mirrors
    DocumentCreationResult's frozen-dataclass shape.
    """

    content: bytes
    media_type: str
    # The plain (un-encoded) download filename, derived from the document title by
    # ExportDocument. Defaults so callers that predate the title wiring (the rest
    # router still hardcodes its Content-Disposition until the Sc 3.1 rest step)
    # keep constructing a RenderedExport; the usecase always supplies it.
    filename: str = "document.pdf"
