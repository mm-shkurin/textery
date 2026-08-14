from dataclasses import dataclass

from document.export_format import ExportFormat


@dataclass(frozen=True)
class RenderedExport:
    """What ExportDocument returns on the found path.

    A bare `bytes` cannot tell the router what it is holding, so the rendered
    payload travels with the format it was rendered under. The FORMAT, not the
    media type: `application/pdf` is an HTTP wire detail, and a usecase that
    named it would be speaking the delivery protocol. The rest adapter maps
    format to Content-Type. Mirrors DocumentCreationResult's frozen-dataclass
    shape.
    """

    content: bytes
    export_format: ExportFormat
    # The plain (un-encoded) download filename, derived from the document title by
    # ExportDocument. Required: the rest router now RFC 5987 encodes it into the
    # Content-Disposition, so every construction site supplies it explicitly.
    filename: str
