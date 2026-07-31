from dataclasses import dataclass

from clients.application.dto.document.raw_response_dto import RawResponseDto


@dataclass(frozen=True)
class GuardSetup:
    """The world scenario 1.1 needs before anything is invoked: an authenticated
    caller, a document owned by a DIFFERENT account, and an id that matches no document.

    `document_before` is the owner's view of their document taken before any probe, so
    "nothing was written" is compared against a captured baseline rather than assumed.
    `owner_token` is carried because the aftermath must be read as the document's
    rightful owner — the caller under test can never see it.
    """

    caller_token: str
    owner_token: str
    foreign_document_id: str
    absent_document_id: str
    document_before: RawResponseDto


@dataclass(frozen=True)
class GuardProbe:
    """One endpoint probed twice: against a foreign document and an absent one.

    The setup is carried alongside both refusals so the aftermath can be read through
    the owner's rightful path afterwards — a refusal that still wrote a row would
    satisfy the 404 assertions alone.
    """

    endpoint: str
    foreign: RawResponseDto
    absent: RawResponseDto
    setup: GuardSetup

    @property
    def owner_token(self) -> str:
        return self.setup.owner_token

    @property
    def foreign_document_id(self) -> str:
        return self.setup.foreign_document_id

    @property
    def document_before(self) -> RawResponseDto:
        return self.setup.document_before


@dataclass(frozen=True)
class DocumentAftermath:
    """Everything the owner can observe about the document after the refused probes."""

    messages: RawResponseDto
    revisions: RawResponseDto
    document_after: RawResponseDto
