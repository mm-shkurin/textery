from dataclasses import dataclass
from datetime import datetime

from clients.application.dto.document.raw_response_dto import RawResponseDto


@dataclass(frozen=True)
class CrossDocumentSetup:
    """The world scenario 1.2 needs before anything is probed: one account, two of its
    documents, and a REAL edit queued on the first.

    Both documents belong to the SAME authenticated caller, so nothing here is an
    ownership question — the refusal must come from the path document id being
    authoritative over the edit id, not from the account check.

    `queued_before`/`queued_after` bracket the queue call so the edit's server-set
    `created_at` can be bounded to the window the test itself observed, rather than
    merely checked for presence.
    """

    owner_token: str
    first_document_id: str
    second_document_id: str
    edit_id: str
    queued_before: datetime
    queued_after: datetime


@dataclass(frozen=True)
class CrossDocumentProbe:
    """One edge of scenario 1.2: that real edit, asked for under the wrong document.

    The setup is carried alongside the refusal so the edit can be read back through its
    own rightful path afterwards: a refused `/cancel` that still terminalized the edit
    would satisfy the 404 assertion alone.
    """

    endpoint: str
    refusal: RawResponseDto
    setup: CrossDocumentSetup

    @property
    def owner_token(self) -> str:
        return self.setup.owner_token

    @property
    def edit_id(self) -> str:
        return self.setup.edit_id

    @property
    def queued_before(self) -> datetime:
        return self.setup.queued_before

    @property
    def queued_after(self) -> datetime:
        return self.setup.queued_after

    @property
    def first_document_id(self) -> str:
        return self.setup.first_document_id

    @property
    def second_document_id(self) -> str:
        return self.setup.second_document_id
