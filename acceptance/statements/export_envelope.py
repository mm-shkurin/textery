"""Format-generic assertion kit for a successful document export.

Every export scenario — pdf happy path, docx happy path, filename derivation,
default filename — needs the same knowledge: which content type a format must
return, which magic bytes prove the payload is real, and that a binary export
carries no parsed JSON body. Holding that knowledge once here keeps the per-format
Statements classes to their own delta and stops the signatures/content types from
drifting apart across three independent copies.

Nothing here touches auth, document setup, or any scenario-specific constant, so
it is a plain module of functions rather than a mixin.
"""

from dataclasses import dataclass
from typing import Optional

from clients.application.dto.document.export_response_dto import ExportResponseDto

PDF_CONTENT_TYPE = "application/pdf"
DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
# The exact content type each export format must return — pinned so a docx export
# can never ship pdf bytes (or a pdf content type) under a .docx filename.
CONTENT_TYPE_BY_FORMAT = {"pdf": PDF_CONTENT_TYPE, "docx": DOCX_CONTENT_TYPE}
# The leading magic bytes of each format: %PDF- for PDF, the PK zip local-file
# header for DOCX (an OOXML package is a zip).
CONTENT_SIGNATURE_BY_FORMAT = {"pdf": b"%PDF-", "docx": b"PK\x03\x04"}


@dataclass(frozen=True)
class ExpectedExportEnvelope:
    """The deterministic part of a successful export response — everything except the
    generated document bytes. A frozen dataclass compares all fields at once, so one
    equality pins status, content type, filename header and the absence of a JSON body
    together rather than leaving unasserted fields free to regress."""

    status_code: int
    content_type: str
    content_disposition: Optional[str]
    body: Optional[dict]


def envelope_of(response: ExportResponseDto) -> ExpectedExportEnvelope:
    return ExpectedExportEnvelope(
        status_code=response.status_code,
        content_type=response.content_type,
        content_disposition=response.content_disposition,
        body=response.body,
    )


def assert_content_signature(response: ExportResponseDto, export_format: str) -> None:
    signature = CONTENT_SIGNATURE_BY_FORMAT[export_format]
    assert response.content.startswith(signature), (
        f"expected a real {export_format} payload starting with the {signature!r} "
        f"signature, got first bytes={response.content[:8]!r}"
    )


def assert_export_envelope(
    response: ExportResponseDto,
    export_format: str,
    expected_content_disposition: str,
    described_as: str,
) -> None:
    """Exact-equality assertion for an export whose filename header is known up front."""
    expected = ExpectedExportEnvelope(
        status_code=200,
        content_type=CONTENT_TYPE_BY_FORMAT[export_format],
        content_disposition=expected_content_disposition,
        body=None,
    )
    actual = envelope_of(response)
    assert actual == expected, (
        f"expected {described_as} — i.e. the export response envelope {expected!r} "
        f"— got {actual!r}"
    )
    assert_content_signature(response, export_format)


def assert_export_attachment(response: ExportResponseDto, export_format: str) -> None:
    """The format-generic half of "a successful export delivered a real attachment":
    200, the exact content type, the format's magic bytes, an attachment disposition,
    and no parsed JSON body. Used where the expected filename is not part of the
    scenario — the disposition is only required to *be* an attachment."""
    expected_content_type = CONTENT_TYPE_BY_FORMAT[export_format]
    assert response.status_code == 200, (
        f"expected 200 exporting the owner's own document as {export_format}, got "
        f"status_code={response.status_code}, body={response.body}"
    )
    assert response.content_type == expected_content_type, (
        f"expected the exact {export_format} content type {expected_content_type!r}, "
        f"got content_type={response.content_type!r}"
    )
    assert_content_signature(response, export_format)
    assert response.content_disposition is not None and (
        response.content_disposition.strip().lower().startswith("attachment")
    ), (
        f"expected a Content-Disposition delivering the export as an attachment, got "
        f"content_disposition={response.content_disposition!r}"
    )
    assert response.body is None, (
        f"a {export_format.upper()} export carries binary bytes, not a parsed JSON "
        f"body — got {response.body!r}"
    )
