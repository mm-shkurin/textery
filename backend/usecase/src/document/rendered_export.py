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
