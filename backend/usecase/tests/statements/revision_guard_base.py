from uuid import UUID

from document_edit.resolve_owned_revision import resolve_owned_revision
from document_edit.revision_scope import RevisionScope

from document.document_repository import DocumentRepository
from fake.document_edit.fake_document_revision_repository import FakeDocumentRevisionRepository
from shared.exceptions import NotFoundException
from statements.document_arrangement import DocumentArrangement
from statements.document_guard_contract import CALLER_ID, assert_lookups, captured

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


class RevisionGuardBase(DocumentArrangement):
    """Arrangement shared by the revision-scope guard's Statements classes.

    One owner, two of their own documents, the first carrying the two revisions a
    single applied edit records: the exact shape §1.3 needs, and the shape every
    other guard here probes from a different angle.
    """

    def __init__(self) -> None:
        super().__init__()
        self.revision_repository = FakeDocumentRevisionRepository()

    async def given_a_revision_recorded_on_the_first_document(self) -> None:
        """The rows, and the mutation that is the only way to get them.

        Async, and it writes: a document holding these two rows has been through
        `save_content_if_version_matches`, so seeding the rows alone would leave the
        store at a version production cannot pair with them -- and the version guard
        would then require that impossible state of the guard under test.
        """
        self.revision_repository.seed_revision(
            BASELINE_REVISION_ID, BASELINE_REVISION_NUMBER, self.first_document_id
        )
        self.revision_repository.seed_revision(
            RECORDED_REVISION_ID, RECORDED_REVISION_NUMBER, self.first_document_id
        )
        await self.apply_an_edit_to_the_first_document()

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

        It is also the one place every act step of this family passes through, which
        is why the arrangement snapshot is taken here rather than by a `given_` step
        each test would have to remember.
        """
        self.capture_the_versions_as_arranged(document_repository)
        return await resolve_owned_revision(
            document_repository,
            self.revision_repository,
            document_id=document_id,
            revision_number=revision_number,
            owner_id=CALLER_ID,
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
