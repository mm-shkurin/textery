from dataclasses import fields
from datetime import UTC, datetime
from uuid import UUID

from document.create_document import CreateDocument
from document.document_scope import DocumentScope
from document.resolve_owned_document import resolve_owned_document
from shared.exceptions import NotFoundException
from statements.arranged import arranged
from statements.document_fakes import FakeClock, FakeDocumentRepository

_EPOCH = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)

_CALLER_ID = UUID("00000000-0000-0000-0000-000000000001")
_OTHER_ACCOUNT_ID = UUID("00000000-0000-0000-0000-000000000002")
_ABSENT_DOCUMENT_ID = UUID("00000000-0000-0000-0000-000000000099")

# The one canonical refusal body the ADR requires of all seven endpoints, defined
# here because the test is the specification: the guard must be written to this
# string, not the other way round. It names no document and carries no
# instruction text -- `not_found_exception_handler` logs the exception verbatim at
# INFO, so anything in here lands in the log of a request whose whole premise is
# that the caller has no claim to that id.
REFUSAL_MESSAGE = "document not found"

# The bounded projection, pinned as a field list rather than only by equality: a
# `content` field added later with a default would still satisfy dataclass
# equality, and the guarantee that the guard never materialises the largest
# column in the schema would die silently.
SCOPE_FIELD_NAMES = ["id", "owner_id"]


class DocumentScopeGuardStatements:
    """The shared document-scope guard the seven AI-edit usecases open with."""

    def __init__(self) -> None:
        self._repository = FakeDocumentRepository()
        self._create_document = CreateDocument(self._repository, FakeClock(_EPOCH))
        self._own_document_id: UUID | None = None
        self._foreign_document_id: UUID | None = None
        self._foreign_refusal: NotFoundException | None = None
        self._absent_refusal: NotFoundException | None = None
        self._resolved_scope: DocumentScope | None = None

    async def given_the_caller_owns_a_document(self) -> None:
        self._own_document_id = await self._seed(owner_id=_CALLER_ID, key="key-own")

    async def given_a_document_owned_by_another_account(self) -> None:
        self._foreign_document_id = await self._seed(owner_id=_OTHER_ACCOUNT_ID, key="key-foreign")

    def given_a_document_id_that_does_not_exist(self) -> None:
        # Nothing to seed: the id is absent precisely because no given_* step
        # writes it. Named as a step anyway so the scenario reads in full.
        pass

    async def _seed(self, owner_id: UUID, key: str) -> UUID:
        # Seeded through the real creation usecase rather than repository.save_new:
        # a hand-built row can hold a shape the application can never produce, and
        # the guard would then be proven against a document that cannot exist.
        result = await self._create_document.execute(
            owner_id=owner_id, document_type="эссе", idempotency_key=key
        )
        return result.document.id

    async def resolve_the_foreign_document(self) -> None:
        self._foreign_refusal = await self._refusal_of(
            arranged(self._foreign_document_id, "foreign_document_id")
        )

    async def resolve_the_absent_document(self) -> None:
        self._absent_refusal = await self._refusal_of(_ABSENT_DOCUMENT_ID)

    async def _refusal_of(self, document_id: UUID) -> NotFoundException:
        try:
            await resolve_owned_document(self._repository, document_id, _CALLER_ID)
        except NotFoundException as refusal:
            return refusal
        raise AssertionError(
            f"expected NotFoundException for document {document_id}, but the guard returned"
        )

    async def resolve_the_callers_own_document(self) -> None:
        self._resolved_scope = await resolve_owned_document(
            self._repository,
            arranged(self._own_document_id, "own_document_id"),
            _CALLER_ID,
        )

    def assert_both_refusals_are_the_one_canonical_not_found(self) -> None:
        """Identity, non-disclosure and exception type in one equality each.

        Comparing the two refusals to each other would pass for a guard that
        raised an empty message for both, or one that leaked the same template
        with the id in it. Comparing each to the literal the ADR fixes settles all
        three properties: same exact type, byte-identical body, and a body that
        provably contains neither document id nor any instruction text.
        """
        self._assert_is_the_canonical_refusal(
            arranged(self._foreign_refusal, "foreign_refusal"), "foreign-document"
        )
        self._assert_is_the_canonical_refusal(
            arranged(self._absent_refusal, "absent_refusal"), "absent-document"
        )

    def _assert_is_the_canonical_refusal(self, refusal: NotFoundException, which: str) -> None:
        # Named once so the two refusals cannot drift apart: whatever "canonical"
        # comes to mean, both are held to the same single expression of it.
        assert (type(refusal), str(refusal)) == (NotFoundException, REFUSAL_MESSAGE), (
            f"the {which} refusal is {type(refusal).__name__}('{refusal}'), expected "
            f"NotFoundException('{REFUSAL_MESSAGE}')"
        )

    def assert_the_own_document_resolved_to_its_scope(self) -> None:
        own_id = arranged(self._own_document_id, "own_document_id")
        scope = arranged(self._resolved_scope, "resolved_scope")
        assert scope == DocumentScope(id=own_id, owner_id=_CALLER_ID), (
            f"expected DocumentScope(id={own_id}, owner_id={_CALLER_ID}), got {scope}"
        )
        assert [field.name for field in fields(scope)] == SCOPE_FIELD_NAMES, (
            f"DocumentScope must stay the bounded projection {SCOPE_FIELD_NAMES}, but carries "
            f"{[field.name for field in fields(scope)]} -- content must never be materialised"
        )
