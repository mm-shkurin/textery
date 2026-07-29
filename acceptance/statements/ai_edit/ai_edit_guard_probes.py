from dataclasses import dataclass

from clients.application.dto.document.raw_response_dto import RawResponseDto


@dataclass(frozen=True)
class GuardProbe:
    """One endpoint probed twice: against a foreign document and an absent one.

    `owner_token` and `foreign_document_id` are carried so the aftermath can be read
    as the document's rightful owner — the caller under test can never see it.
    `document_before` is the owner's view of the document taken before the probes, so
    "nothing was written" is compared against a captured baseline rather than assumed.
    """

    endpoint: str
    foreign: RawResponseDto
    absent: RawResponseDto
    owner_token: str
    foreign_document_id: str
    document_before: RawResponseDto


@dataclass(frozen=True)
class DocumentAftermath:
    """Everything the owner can observe about the document after the refused probes."""

    messages: RawResponseDto
    revisions: RawResponseDto
    document_after: RawResponseDto
