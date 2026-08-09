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
        write, and the refusal assertions cannot see writes: a guard that refused
        correctly and bumped a version on the way past satisfies every other
        assertion here. One whole-store equality against the minted literal, for
        the arrangement seeding the caller's own two and nothing else; probes at a
        document the caller cannot resolve seed a third row and use the sibling.
        """
        self._assert_versions(
            {
                self.first_document_id: NEW_DOCUMENT_VERSION,
                self.second_document_id: NEW_DOCUMENT_VERSION,
            }
        )

    def assert_no_probed_document_gained_a_version(self) -> None:
        """The same claim, for the arrangement an unresolvable probe touches.

        A guard that refused correctly, emitted the right step-1 record and bumped
        the *foreign* document's version on the way past satisfied every assertion
        the unresolvable-probe test had, because nothing read that document's
        version. The absent id needs no entry: an id missing from the expected
        mapping is one the store is required not to hold at all.
        """
        self._assert_versions(
            {
                self.first_document_id: NEW_DOCUMENT_VERSION,
                self.second_document_id: NEW_DOCUMENT_VERSION,
                self.foreign_document_id: NEW_DOCUMENT_VERSION,
            }
        )

    def _assert_versions(self, expected: dict[UUID, int]) -> None:
        """The whole store, keyed by id, against a mapping the caller wrote out.

        Read as `{id: version}` over every row rather than by looking up the ids
        the caller named: a per-id probe can only fail on a row somebody thought to
        enumerate, so a guard that *inserted* a row -- under the absent id it was
        handed, or under one it minted -- passed the aimed form of this assertion
        whichever ids it was aimed at. Comparing the store whole puts the row set
        inside the equality, so a version that moved and a row that appeared fail
        the same expression, and no `None` arm is needed to ask about an id that
        owns no row -- removing the way a `None` stood for "never seeded" too.

        The expected side is literal versions against arrangement-minted ids, never
        read back off `documents`: an expectation sampled from the store agrees
        with whatever the guard did to it, including bumping.
        """
        actual = {row.id: row.version for row in self.document_repository.documents}
        assert actual == expected, (
            f"the store holds versions {actual}, expected {expected} -- resolving a revision is a "
            f"read, and a guard writing on the refusal path satisfies every other assertion here "
            f"while a document silently moves or appears"
        )

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
