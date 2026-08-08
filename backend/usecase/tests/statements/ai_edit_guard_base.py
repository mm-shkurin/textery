from uuid import UUID

from document_edit.ai_edit_scope import AiEditScope
from document_edit.resolve_owned_edit import resolve_owned_edit

from document.create_document import CreateDocument
from document.document_repository import DocumentRepository
from fake.document_edit.fake_ai_edit_repository import FakeAiEditRepository
from shared.exceptions import NotFoundException
from statements.arranged import arranged
from statements.document_fakes import FakeClock, FakeDocumentRepository
from statements.document_guard_contract import (
    CALLER_ID,
    EPOCH,
    OTHER_ACCOUNT_ID,
    assert_lookups,
    captured,
)

QUEUED_EDIT_ID = UUID("00000000-0000-0000-0000-0000000000e1")

# The bounded projection, pinned by literal name list rather than derived from
# `dataclasses.fields(AiEditScope)`: a guard derived from the thing it guards
# widens the moment the thing widens. An `instruction` or `diff` field added
# later would still satisfy dataclass equality, and the promise that the guard
# path never materialises edit content would die without a single red test.
#
# Qualified by scope name: 1.1 pins a list under the same bare `SCOPE_FIELD_NAMES`
# with deliberately *different* values, and two same-named constants that must
# stay different is the drift trap the qualified names close.
AI_EDIT_SCOPE_FIELD_NAMES = ["id", "document_id"]


class AiEditGuardBase:
    """Arrangement shared by the edit-scope guard's Statements classes.

    One owner, two of their own documents, one edit queued on the first: the
    exact shape §1.2 needs, and the shape every other guard here probes from a
    different angle.
    """

    def __init__(self) -> None:
        self.document_repository = FakeDocumentRepository()
        self.ai_edit_repository = FakeAiEditRepository()
        self._create_document = CreateDocument(self.document_repository, FakeClock(EPOCH))
        self._first_document_id: UUID | None = None
        self._second_document_id: UUID | None = None
        self._foreign_document_id: UUID | None = None

    async def given_the_caller_owns_two_documents(self) -> None:
        # Seeded through the real creation usecase rather than repository.save_new:
        # a hand-built row can hold a shape the application can never produce, and
        # the guard would then be proven against documents that cannot exist.
        self._first_document_id = await self._seed(CALLER_ID, "key-first")
        self._second_document_id = await self._seed(CALLER_ID, "key-second")

    async def given_a_document_owned_by_another_account(self) -> None:
        self._foreign_document_id = await self._seed(OTHER_ACCOUNT_ID, "key-foreign")

    def given_an_edit_queued_on_the_first_document(self) -> None:
        self.ai_edit_repository.seed_queued_edit(QUEUED_EDIT_ID, self.first_document_id)

    async def _seed(self, owner_id: UUID, key: str) -> UUID:
        result = await self._create_document.execute(
            owner_id=owner_id, document_type="эссе", idempotency_key=key
        )
        return result.document.id

    @property
    def first_document_id(self) -> UUID:
        return arranged(self._first_document_id, "first_document_id")

    @property
    def second_document_id(self) -> UUID:
        return arranged(self._second_document_id, "second_document_id")

    @property
    def foreign_document_id(self) -> UUID:
        return arranged(self._foreign_document_id, "foreign_document_id")

    async def resolve(self, document_id: UUID) -> AiEditScope:
        return await self.resolve_via(self.document_repository, document_id)

    async def resolve_via(
        self, document_repository: DocumentRepository, document_id: UUID
    ) -> AiEditScope:
        """The one place the guard's argument order is written down.

        The outage statements used to rebuild this call themselves in order to
        swap in a failing document repository, which pinned the order of five
        arguments -- three of them same-typed UUIDs -- in two files at once.
        Taking the repository as the parameter that actually varies leaves one
        call site for the resolver in the whole test suite.
        """
        return await resolve_owned_edit(
            document_repository,
            self.ai_edit_repository,
            document_id=document_id,
            edit_id=QUEUED_EDIT_ID,
            owner_id=CALLER_ID,
        )

    def assert_edit_lookups(self, expected: list[tuple[UUID, UUID]], why: str) -> None:
        """The edit store's call log, compared whole.

        Both subclasses assert on this same spy from four methods, and every one
        of them had its own copy of the comparison. The comparison itself is
        `assert_lookups`, shared with the revision guard; this method is the spy
        it reads and the noun its failure uses.
        """
        assert_lookups("edit", list(self.ai_edit_repository.lookups), list(expected), why)

    async def refusal_of(self, document_id: UUID) -> NotFoundException:
        return await captured(
            self.resolve(document_id),
            NotFoundException,
            f"NotFoundException for edit {QUEUED_EDIT_ID} under document {document_id}",
        )
