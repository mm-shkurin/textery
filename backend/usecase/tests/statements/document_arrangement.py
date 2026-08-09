"""The document store every scope guard arranges against, and the write none may take.

`ai_edit_guard_base` and `revision_guard_base` had grown byte-identical copies of
this arrangement -- the same two owned documents, the same foreign one, the same
`_seed` through the real creation usecase, the same three properties -- and
`document_scope_guard_statements` a third variant of it under different names.
Written once here so the three families cannot drift apart, and so the version
guard below covers all three rather than the single test that happened to ask.

The version guard is the part that was missing everywhere. Resolving a scope is a
read; "no new version is created" is a claim about a *write*, and no refusal
assertion in any of the three families could see one. A guard that refused
correctly and bumped -- or inserted -- a row on the way past satisfied every
assertion all three packages had.

Two separate statements, deliberately not one:

* `assert_the_arrangement_holds_the_minted_versions` compares the snapshot taken at
  the end of the arrangement against versions the `given_` steps named as literals.
  It fails when the *arrangement* is not a shape production can produce.
* `assert_no_document_gained_a_version` compares the store now against that
  snapshot. It fails when the *guard* wrote.

One whole-store equality against a per-test hardcoded mapping conflated the two:
adding a `given_` step to a test for an unrelated reason failed with text pointing
at production, and the cheapest diagnosis was to loosen back to enumerated ids --
reopening the very hole the whole-store form exists to close.
"""

from uuid import UUID

from document.create_document import CreateDocument
from document.save_document import SaveDocument
from statements.arranged import arranged
from statements.document_fakes import FakeClock, FakeDocumentRepository, FakeHtmlSanitizer
from statements.document_guard_contract import CALLER_ID, EPOCH, OTHER_ACCOUNT_ID

# What `Document.create` mints, written as the literal rather than read back off the
# seeded row: an expectation sampled from the thing under observation agrees with
# whatever the guard did to it, including incrementing it.
NEW_DOCUMENT_VERSION = 1

# And what the store holds once that document has taken one applied edit. A document
# carrying revision rows has been through `save_content_if_version_matches`, which
# increments -- so an arrangement that seeds the rows and leaves the version at 1
# pins a store state production cannot produce.
POST_EDIT_DOCUMENT_VERSION = 2

APPLIED_EDIT_CONTENT = "the content the first applied edit left behind"


class DocumentArrangement:
    """One owner with two documents, another account with one, and their versions."""

    def __init__(self) -> None:
        self.document_repository = FakeDocumentRepository()
        self._create_document = CreateDocument(self.document_repository, FakeClock(EPOCH))
        self._save_document = SaveDocument(
            self.document_repository, FakeHtmlSanitizer(), FakeClock(EPOCH)
        )
        self._minted_versions: dict[UUID, int] = {}
        self._versions_as_arranged: dict[UUID, int] | None = None
        self._acted_on_a_store_outside_the_arrangement = False
        self._first_document_id: UUID | None = None
        self._second_document_id: UUID | None = None
        self._foreign_document_id: UUID | None = None

    async def given_the_caller_owns_two_documents(self) -> None:
        self._first_document_id = await self._seed(CALLER_ID, "key-first")
        self._second_document_id = await self._seed(CALLER_ID, "key-second")

    async def given_the_caller_owns_a_document(self) -> None:
        self._first_document_id = await self._seed(CALLER_ID, "key-own")

    async def given_a_document_owned_by_another_account(self) -> None:
        self._foreign_document_id = await self._seed(OTHER_ACCOUNT_ID, "key-foreign")

    async def _seed(self, owner_id: UUID, key: str) -> UUID:
        # Seeded through the real creation usecase rather than repository.save_new:
        # a hand-built row can hold a shape the application can never produce, and
        # the guard would then be proven against documents that cannot exist.
        result = await self._create_document.execute(
            owner_id=owner_id, document_type="эссе", idempotency_key=key
        )
        self._minted_versions[result.document.id] = NEW_DOCUMENT_VERSION
        return result.document.id

    async def apply_an_edit_to_the_first_document(self) -> None:
        """Take the document through the mutation its revision rows imply.

        Through `SaveDocument` -- the usecase that owns the write the applied edit
        performs -- rather than by assigning `version` on the stored row: the same
        principle `_seed` states about creation, applied to the mutation. The
        post-edit version is then named as a literal, not read back off the row the
        usecase just wrote.
        """
        await self._save_document.execute(
            document_id=self.first_document_id,
            owner_id=CALLER_ID,
            content=APPLIED_EDIT_CONTENT,
            version=NEW_DOCUMENT_VERSION,
        )
        self._minted_versions[self.first_document_id] = POST_EDIT_DOCUMENT_VERSION

    def capture_the_versions_as_arranged(self, acted_on: object) -> None:
        """The end of the arrangement, taken at the first act rather than declared.

        Lazy and idempotent rather than an explicit `given_` step: a step would have
        to be remembered in every test of three packages, and the one test that
        forgot would be the one whose guard wrote.

        `acted_on` is the document store the act was actually handed, and it is a
        required argument for a reason. The outage families deliberately pass a
        *failing* repository into `resolve_via`, while the snapshot can only ever be
        read off `self.document_repository` -- so a version assertion added to one of
        those tests would compare a store the guard never touched and pass no matter
        what the guard did. Harmless only for as long as nobody adds the assertion,
        which is exactly the kind of quiet the version guard exists to end: the whole
        claim of the lazy snapshot is that no test has to remember anything.

        The mismatch cannot be resolved by snapshotting the substitute (a failing
        double holds no rows at all), so it is recorded and made to fail loudly at
        the assertions instead of silently agreeing with itself.
        """
        if acted_on is not self.document_repository:
            self._acted_on_a_store_outside_the_arrangement = True
        if self._versions_as_arranged is None:
            self._versions_as_arranged = self._versions_now()

    def _refuse_a_snapshot_of_a_store_the_act_never_used(self) -> None:
        assert not self._acted_on_a_store_outside_the_arrangement, (
            "the act was handed a document store other than this arrangement's, so the "
            "version snapshot describes rows the guard never touched -- the assertion would "
            "hold no matter what the guard did. Assert versions on a path that acts on "
            "`self.document_repository`, or teach the substitute to expose its rows"
        )

    def assert_the_arrangement_holds_the_minted_versions(self) -> None:
        """The arranged store is the shape production produces, and nothing else.

        What this guards is the *versions*, and it guards them against literals:
        `_minted_versions` is filled by `_seed` and `apply_an_edit_...` from the two
        constants above, never read back off the row, so a creation that minted 5 or
        an applied edit that left the row at 1 fails here.

        What it does not guard is the roster. Every document in this arrangement is
        written by `_seed`, which registers the same id on both sides of the
        equality, so a `given_` step that seeded a third document agrees with itself.
        That is an arrangement-authoring error, not a production write, and closing
        it would mean naming ids the creation usecase mints -- which the test cannot
        write as literals. `assert_no_document_gained_a_version` is the one that sees
        rows appear, because its expectation is a snapshot taken before the act.
        """
        self._refuse_a_snapshot_of_a_store_the_act_never_used()
        actual = arranged(self._versions_as_arranged, "versions_as_arranged")
        assert actual == self._minted_versions, (
            f"the arrangement left versions {actual}, expected {self._minted_versions} -- the "
            f"given_ steps must leave a store production could have produced, or the guard is "
            f"proven against documents that cannot exist"
        )

    def assert_no_document_gained_a_version(self) -> None:
        """The store after the act, against the snapshot taken before it.

        Compared against the snapshot rather than a mapping each test writes out:
        the hardcoded form was silently coupled to which `given_` steps ran, so a
        test that arranged one more document failed here, in production's words,
        for an arrangement reason.

        Compared whole for the same reason as above, and one further: a guard that
        *inserted* a row -- under the absent id it was handed, or under one it
        minted -- passes any aimed form of this assertion. The row set is inside
        the equality, so a version that moved and a row that appeared fail the same
        expression.
        """
        self._refuse_a_snapshot_of_a_store_the_act_never_used()
        expected = arranged(self._versions_as_arranged, "versions_as_arranged")
        actual = self._versions_now()
        assert actual == expected, (
            f"the store holds versions {actual}, expected {expected} as arranged -- resolving a "
            f"scope is a read, and a guard writing on the refusal path satisfies every other "
            f"assertion here while a document silently moves or appears"
        )

    def _versions_now(self) -> dict[UUID, int]:
        return {row.id: row.version for row in self.document_repository.documents}

    @property
    def first_document_id(self) -> UUID:
        return arranged(self._first_document_id, "first_document_id")

    @property
    def second_document_id(self) -> UUID:
        return arranged(self._second_document_id, "second_document_id")

    @property
    def foreign_document_id(self) -> UUID:
        return arranged(self._foreign_document_id, "foreign_document_id")
