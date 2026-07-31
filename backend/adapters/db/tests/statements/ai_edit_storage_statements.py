"""DSL for the AI-edit storage adapter's tests (Scenario 1.2).

**Seam, declared rather than hidden.** The edits are seeded straight onto the
model, one layer below the port. The house rule is write-here-read-there -- seed
through the writer usecase's port, read through the reader's -- but the writer is
`QueueAiEdit`, which scenario 3.1 owns and which does not exist yet. Convert
`given_a_queued_edit` to the real write->read flow when 3.1 lands; the adapters-
discovery entry for 1.2 records the same deferral.

**Why the production model is resolved lazily.**
`model/document_edit/ai_edit_model.py` does not exist during RED. Importing it at
module scope would raise inside the fixture, so pytest would report setup *errors*
instead of failing tests -- a red that never reaches the call phase and reads, in
a summary line, like a broken checkout rather than an unimplemented adapter.
Collapse to a module-scope import at GREEN.

The adapter's static shape guards (keyword-only ids, structural conformance) live
in `ai_edit_port_shape_statements`: they touch no session and no row.
"""

from uuid import UUID, uuid4

from document_edit.ai_edit_scope import AiEditScope
from sqlalchemy.ext.asyncio import AsyncSession

from statements.document_storage_statements import DocumentStorageStatements
from statements.sql_recorder import WatchedRead, recording_sql

# The projection the ADR pins, written out as the spec rather than derived from
# `dataclasses.fields(AiEditScope)`: a list read off the DTO widens the day the DTO
# widens, so it could never fail on the drift it exists to catch (1.1's lesson).
# Kept sorted because the comparison is order-insensitive -- `SELECT document_id, id`
# is a correct green. The table qualifier is part of the literal: without it, two
# same-named columns projected off a joined or wrong table satisfy an assertion whose
# whole claim is "it read only its **own** columns".
# `document_edit_scope_statements` carries the unqualified twin on the usecase side.
AI_EDIT_SCOPE_COLUMNS = ["ai_edits.document_id", "ai_edits.id"]


def _ai_edit_model():
    from model.document_edit.ai_edit_model import AiEditModel

    return AiEditModel


class AiEditStorageStatements:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._documents = DocumentStorageStatements(session)

    def _storage(self):
        from access.document_edit.ai_edit_storage import SqlAlchemyAiEditStorage

        return SqlAlchemyAiEditStorage(self._session)

    async def _given_a_document(self) -> UUID:
        owner_id = await self._documents.given_an_account()
        return (await self._documents.given_a_saved_document(owner_id)).id

    async def _given_a_queued_edit(self, document_id: UUID) -> UUID:
        """Seed one edit under `document_id`. See the module docstring's seam note."""
        edit_id = uuid4()
        self._session.add(_ai_edit_model()(id=edit_id, document_id=document_id))
        await self._session.commit()
        return edit_id

    async def given_a_document_with_a_queued_edit(self) -> tuple[UUID, UUID]:
        """A document of some owner, and one edit of that same document."""
        document_id = await self._given_a_document()
        return document_id, await self._given_a_queued_edit(document_id)

    async def given_an_edit_under_another_document_of_the_same_owner(
        self,
    ) -> tuple[UUID, UUID]:
        """Two documents of ONE owner, with the edit seeded under the second.

        Deliberately the same owner: owner scoping is 1.1's job, and a different
        owner would let a missing `document_id` predicate hide behind it. Returns
        the *first* document -- the one the edit does not belong to.
        """
        owner_id = await self._documents.given_an_account()
        document_id = (await self._documents.given_a_saved_document(owner_id)).id
        other_document_id = (await self._documents.given_a_saved_document(owner_id)).id
        return document_id, await self._given_a_queued_edit(other_document_id)

    async def find_scope(self, edit_id: UUID, document_id: UUID) -> AiEditScope | None:
        return await self._storage().find_scope_by_id_and_document(
            edit_id=edit_id, document_id=document_id
        )

    async def find_scope_of_an_absent_edit(self, document_id: UUID) -> AiEditScope | None:
        """Ask for an edit id no `given_*` step ever seeded.

        Minted here so the absence is a property of the step rather than of a
        `uuid4()` the reader has to trace back through the test body.
        """
        return await self.find_scope(uuid4(), document_id)

    async def find_scope_watching_what_it_reads(
        self, edit_id: UUID, document_id: UUID
    ) -> WatchedRead[AiEditScope]:
        with recording_sql(self._session) as recorded:
            scope = await self.find_scope(edit_id, document_id)
        return WatchedRead(scope, recorded)

    def assert_scope_matches(self, actual: AiEditScope | None, edit_id: UUID, document_id: UUID):
        assert actual is not None, (
            "the document's own edit must resolve to a scope. A finder that answers None here "
            "refuses every owner their own edit while the usecase suite -- which runs against "
            "the fake -- stays entirely green."
        )
        # Whole-dataclass equality, not a field tuple: an enumeration silently
        # stops covering the DTO the day it grows a field, which is the same day
        # the bounded projection would need re-proving.
        assert actual == AiEditScope(id=edit_id, document_id=document_id), (
            f"the scope must identify the seeded edit: expected "
            f"AiEditScope(id={edit_id}, document_id={document_id}), got {actual}"
        )

    def assert_an_edit_of_another_document_is_not_resolved(self, actual: AiEditScope | None):
        assert actual is None, (
            "an edit belonging to another document must read as absent even when that document "
            "has the same owner -- the path document id is authoritative, and an `id`-only "
            f"predicate is what this case exists to fail. The finder resolved {actual}"
        )

    def assert_an_absent_edit_is_not_resolved(self, actual: AiEditScope | None):
        assert actual is None, (
            "an edit id that was never seeded must resolve to nothing, even under a document "
            "that does have edits -- a `document_id`-only predicate, or a finder echoing its "
            f"arguments back as a scope, is what this case exists to fail. Resolved {actual}"
        )

    def assert_the_scope_was_resolved_reading_only_its_own_columns(
        self, read: WatchedRead[AiEditScope], edit_id: UUID, document_id: UUID
    ) -> None:
        """Identity and projection together, or neither is worth anything.

        A finder that emits one cheap SELECT and returns `None` satisfies the
        projection half alone, so the positive identity is asserted here rather
        than left to a Then step a test could half-write.

        The statement count is pinned at one rather than merely non-empty. Zero
        would make the projection equality vacuously true -- `recording_sql`
        listens on the **sync** engine because a listener on the `AsyncEngine`
        never fires, and that failure is silent in exactly this direction. Two or
        more is the full-entity read *plus* a projection, which is the shape this
        assertion exists to reject and must fail here by name, not further down.
        """
        self.assert_scope_matches(read.answer, edit_id, document_id)
        assert len(read.recorded.statements) == 1, (
            f"the scope read must emit exactly one statement, got "
            f"{len(read.recorded.statements)}: {read.recorded.statements}. Zero means the "
            "finder never reached the database or the listener never fired -- either makes "
            "the projection assertion below vacuously true, which is the failure mode it is "
            "written against. More than one means something else was read alongside it."
        )
        selected = sorted(read.recorded.qualified_selected_columns())
        assert selected == AI_EDIT_SCOPE_COLUMNS, (
            f"the scope read must select exactly {AI_EDIT_SCOPE_COLUMNS}, but selected "
            f"{selected}. It answers a yes/no question on the guard path of all three "
            "edit-scoped endpoints; a full-entity read carries the instruction and the "
            f"generated content with it. Statement: {read.recorded.the_only_statement()}"
        )
