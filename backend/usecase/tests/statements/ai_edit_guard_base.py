from datetime import UTC, datetime
from uuid import UUID

from document_edit.ai_edit_scope import AiEditScope
from document_edit.resolve_owned_edit import resolve_owned_edit

from document.create_document import CreateDocument
from fake.document_edit.fake_ai_edit_repository import FakeAiEditRepository
from shared.exceptions import NotFoundException
from statements.arranged import arranged
from statements.document_fakes import FakeClock, FakeDocumentRepository

_EPOCH = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)

CALLER_ID = UUID("00000000-0000-0000-0000-000000000001")
OTHER_ACCOUNT_ID = UUID("00000000-0000-0000-0000-000000000002")
ABSENT_DOCUMENT_ID = UUID("00000000-0000-0000-0000-000000000099")
QUEUED_EDIT_ID = UUID("00000000-0000-0000-0000-0000000000e1")

# The one canonical refusal body, written as a literal rather than imported from
# `resolve_owned_document`: the test is the specification, so importing the
# constant would make any future edit to it self-approving -- a rename of the
# text would keep both 1.1 and 1.2 green while the acceptance suite's
# byte-identity contract with the client silently changed.
REFUSAL_MESSAGE = "document not found"

# The bounded projection, pinned by literal name list rather than derived from
# `dataclasses.fields(AiEditScope)`: a guard derived from the thing it guards
# widens the moment the thing widens. An `instruction` or `diff` field added
# later would still satisfy dataclass equality, and the promise that the guard
# path never materialises edit content would die without a single red test.
SCOPE_FIELD_NAMES = ["id", "document_id"]


class AiEditGuardBase:
    """Arrangement shared by the edit-scope guard's Statements classes.

    One owner, two of their own documents, one edit queued on the first: the
    exact shape §1.2 needs, and the shape every other guard here probes from a
    different angle.
    """

    def __init__(self) -> None:
        self.document_repository = FakeDocumentRepository()
        self.ai_edit_repository = FakeAiEditRepository()
        self._create_document = CreateDocument(self.document_repository, FakeClock(_EPOCH))
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

    async def resolve(self, document_id: UUID, edit_id: UUID = QUEUED_EDIT_ID) -> AiEditScope:
        return await resolve_owned_edit(
            self.document_repository,
            self.ai_edit_repository,
            document_id,
            edit_id,
            CALLER_ID,
        )

    async def refusal_of(self, document_id: UUID, edit_id: UUID = QUEUED_EDIT_ID) -> Exception:
        try:
            await self.resolve(document_id, edit_id)
        except NotFoundException as refusal:
            return refusal
        raise AssertionError(
            f"expected NotFoundException for edit {edit_id} under document {document_id}, "
            f"but the guard returned"
        )
