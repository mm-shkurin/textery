from dataclasses import dataclass
from datetime import datetime

from clients.application.dto.document.raw_response_dto import RawResponseDto
from statements.ai_edit.ai_edit_document_state import DocumentState

__all__ = [
    "CrossRevisionAftermath",
    "CrossRevisionProbe",
    "CrossRevisionSetup",
]


@dataclass(frozen=True)
class CrossRevisionSetup:
    """The world scenario 1.3 needs: one account, two of its documents, and a REAL
    revision recorded on the first.

    Both documents belong to the SAME authenticated caller, so nothing here is an
    ownership question — the refusal must come from the path document id being
    authoritative over the revision number, not from the account check.

    `first_before`/`second_before` are the pre-probe baselines the aftermath is compared
    against. They are not merely captured, they are pinned to exact spec-derived values
    before the probe runs: the first document must be at version 2 with a two-row
    revision page, the second at version 1 with an EMPTY one. Without that, an aftermath
    of `after == before` would be equally satisfied by a seed that recorded nothing.

    `seed_window` brackets the seeding edit so the recorded revisions' `created_at` can
    be bounded to the interval the test itself observed.
    """

    owner_token: str
    revision_number: int
    seed_window: tuple[datetime, datetime]
    first_before: DocumentState
    second_before: DocumentState

    @property
    def first_document_id(self) -> str:
        return self.first_before.document_id

    @property
    def second_document_id(self) -> str:
        return self.second_before.document_id


@dataclass(frozen=True)
class CrossRevisionProbe:
    """That real revision number, restored under the wrong document's path.

    The setup is carried alongside the refusal so both documents can be re-read
    afterwards: a refusal that restored anyway would satisfy the 404 assertion alone.
    """

    refusal: RawResponseDto
    setup: CrossRevisionSetup

    @property
    def owner_token(self) -> str:
        return self.setup.owner_token

    @property
    def revision_number(self) -> int:
        return self.setup.revision_number

    @property
    def seed_window(self) -> tuple[datetime, datetime]:
        return self.setup.seed_window

    @property
    def first_document_id(self) -> str:
        return self.setup.first_document_id

    @property
    def second_document_id(self) -> str:
        return self.setup.second_document_id

    @property
    def first_before(self) -> DocumentState:
        return self.setup.first_before

    @property
    def second_before(self) -> DocumentState:
        return self.setup.second_before


@dataclass(frozen=True)
class CrossRevisionAftermath:
    """Both documents re-read after the refusal, in the same shape as the baseline."""

    first_after: DocumentState
    second_after: DocumentState
