"""Content-Type per export format — the wire half of an export.

Here rather than in the usecase because a media type is a delivery-protocol
detail: `ExportDocument` decides WHAT was rendered, this decides how HTTP names
it. A usecase holding `application/pdf` is the layer speaking the transport it
is supposed to be independent of, and it makes the map unreachable from any
other delivery path that might one day serve the same bytes.

Keyed by the enum so a new format is a one-line addition rather than a branch,
and exhaustiveness is a test at this layer: an unmapped format raises here
loudly rather than silently serving the wrong Content-Type.
"""

from document.export_format import ExportFormat

MEDIA_TYPE: dict[ExportFormat, str] = {
    ExportFormat.PDF: "application/pdf",
    ExportFormat.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def media_type_for(export_format: ExportFormat) -> str:
    return MEDIA_TYPE[export_format]
