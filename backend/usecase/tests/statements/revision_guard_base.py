from uuid import UUID

from document_edit.resolve_owned_revision import resolve_owned_revision
from document_edit.revision_scope import RevisionScope

from document.create_document import CreateDocument
from document.document_repository import DocumentRepository
from fake.document_edit.fake_document_revision_repository import FakeDocumentRevisionRepository
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

BASELINE_REVISION_ID = UUID("00000000-0000-0000-0000-0000000000a1")
RECORDED_REVISION_ID = UUID("00000000-0000-0000-0000-0000000000a2")

# The two rows the first mutation of a never-edited document writes in one
# transaction (`documents_revisions_list.yaml`): number 1 carries the
# pre-mutation content, number 2 the result. The scenario probes number 2 --
# seeding only the row under test would let a guard that answers "the highest
# number wins", or one that is off by one, resolve for the wrong reason.
BASELINE_REVISION_NUMBER = 1
RECORDED_REVISION_NUMBER = 2

# The parameter reaches the guard as a `str`: the route must not let FastAPI
# coerce it, or a malformed number would be answered 422 ahead of the Bearer
# dependency. Written as the literal the wire actually carries.
RECORDED_REVISION_PARAMETER = "2"

# What `Document.create` mints, written as the literal rather than read back off
# the seeded row: an expectation sampled from the thing under observation agrees
# with whatever the guard did to it, including incrementing it.
NEW_DOCUMENT_VERSION = 1


class RevisionGuardBase:
    """Arrangement shared by the revision-scope guard's Statements classes.

    One owner, two of their own documents, the first carrying the two revisions a
    single applied edit records: the exact shape §1.3 needs, and the shape every
    other guard here probes from a different angle.
    """

    def __init__(self) -> None:
        self.document_repository = FakeDocumentRepository()
        self.revision_repository = FakeDocumentRevisionRepository()
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

    def given_a_revision_recorded_on_the_first_document(self) -> None:
        self.revision_repository.seed_revision(
            BASELINE_REVISION_ID, BASELINE_REVISION_NUMBER, self.first_document_id
        )
        self.revision_repository.seed_revision(
            RECORDED_REVISION_ID, RECORDED_REVISION_NUMBER, self.first_document_id
        )

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

    async def resolve(
        self, document_id: UUID, revision_number: str = RECORDED_REVISION_PARAMETER
    ) -> RevisionScope:
        return await self.resolve_via(self.document_repository, document_id, revision_number)

    async def resolve_via(
        self,
        document_repository: DocumentRepository,
        document_id: UUID,
        revision_number: str = RECORDED_REVISION_PARAMETER,
    ) -> RevisionScope:
        """The one place the guard's argument order is written down.

        Taking the repository as the parameter that actually varies leaves one
        call site for the resolver in the whole suite -- the shape 1.2 arrived at
        after its outage statements had rebuilt the call themselves and pinned a
        five-argument order in two files at once.
        """
        return await resolve_owned_revision(
            document_repository,
            self.revision_repository,
            document_id=document_id,
            revision_number=revision_number,
            owner_id=CALLER_ID,
        )

    def assert_neither_document_gained_a_version(self) -> None:
        """The scenario's last Then, which had no assertion behind it.

        "And no new version is created on either document" is a claim about a
        write, and the refusal assertions cannot see writes at all: a guard that
        refused correctly and bumped a version on the way past would satisfy every
        other assertion in this package. Pinned as one mapping equality against
        the minted literal, so a version that moved on *either* document -- the
        probed one or the one that actually owns the revision -- is named.
        """
        actual = {
            "first": self._version_of(self.first_document_id),
            "second": self._version_of(self.second_document_id),
        }
        expected = {"first": NEW_DOCUMENT_VERSION, "second": NEW_DOCUMENT_VERSION}
        assert actual == expected, (
            f"the two documents are at versions {actual}, expected {expected} -- resolving a "
            f"revision is a read, and a guard that writes on the refusal path would satisfy "
            f"every other assertion here while the caller's document silently moved"
        )

    def _version_of(self, document_id: UUID) -> int:
        stored = next(
            (row for row in self.document_repository.documents if row.id == document_id), None
        )
        assert stored is not None, f"document {document_id} was never seeded"
        return stored.version

    def _assert_revision_lookups(self, expected: list[tuple[int, UUID]], why: str) -> None:
        """The revision store's call log, compared whole.

        Protected rather than public: the expectation is supplied entirely by the
        caller, so a public form lets any collaborator pass `[]` and weaken the
        ordering guard without editing an assertion. Only the intent-named
        wrappers in the subclasses may reach it.

        The comparison itself is `assert_lookups`, shared with the edit guard. What
        this class adds beyond that shared reasoning is the range guard: a guard
        that passed an out-of-range number straight through would refuse
        identically and blow up as a 500 the day a real store is behind the port,
        so the empty list is as load-bearing here as the populated one.
        """
        assert_lookups("revision", list(self.revision_repository.lookups), list(expected), why)

    async def refusal_of(
        self, document_id: UUID, revision_number: str = RECORDED_REVISION_PARAMETER
    ) -> NotFoundException:
        return await captured(
            self.resolve(document_id, revision_number),
            NotFoundException,
            f"NotFoundException for revision '{revision_number}' under document {document_id}",
        )
