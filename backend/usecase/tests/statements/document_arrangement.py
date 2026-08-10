"""The document store every scope guard arranges against, and the ids it names.

`ai_edit_guard_base` and `revision_guard_base` had grown byte-identical copies of
this arrangement -- the same two owned documents, the same foreign one, the same
`_seed` through the real creation usecase, the same three properties -- and
`document_scope_guard_statements` a third variant of it under different names.
Written once here so the three families cannot drift apart, and so the version
guard reached through it covers all three rather than the single test that
happened to ask.

The version guard itself lives in `document_version_ledger`: what the `given_`
steps minted, what the store held at the end of the arrangement, and whether the
act wrote. None of it reads a document id and none of the arranging below reads
it back, so the two were split rather than left sharing a class. The three
delegating methods at the bottom are the seam -- the guard families and their
tests call them unchanged, and the reasoning behind each lives with the ledger.
"""

from uuid import UUID

from document.create_document import CreateDocument
from document.save_document import SaveDocument
from statements.arranged import arranged
from statements.document_fakes import FakeClock, FakeDocumentRepository, FakeHtmlSanitizer
from statements.document_guard_contract import CALLER_ID, EPOCH, OTHER_ACCOUNT_ID
from statements.document_version_ledger import DocumentVersionLedger

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
        self._versions = DocumentVersionLedger(self.document_repository)
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
        self._versions.record_the_minted_version(result.document.id, NEW_DOCUMENT_VERSION)
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
        self._versions.record_the_minted_version(
            self.first_document_id, POST_EDIT_DOCUMENT_VERSION
        )

    def capture_the_versions_as_arranged(self, acted_on: object) -> None:
        self._versions.capture_the_versions_as_arranged(acted_on)

    def assert_the_arrangement_holds_the_minted_versions(self) -> None:
        self._versions.assert_the_arrangement_holds_the_minted_versions()

    def assert_no_document_gained_a_version(self) -> None:
        self._versions.assert_no_document_gained_a_version()

    @property
    def first_document_id(self) -> UUID:
        return arranged(self._first_document_id, "first_document_id")

    @property
    def second_document_id(self) -> UUID:
        return arranged(self._second_document_id, "second_document_id")

    @property
    def foreign_document_id(self) -> UUID:
        return arranged(self._foreign_document_id, "foreign_document_id")
