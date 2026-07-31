from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from access.auth.account_storage import SqlAlchemyAccountRepository
from access.document.document_storage import SqlAlchemyDocumentStorage
from auth.account import Account
from document.document import Document
from document.document_scope import DocumentScope
from statements.sql_recorder import WatchedRead, recording_sql

# The columns the scope read is allowed to select, written out as the spec rather than
# read off `DocumentScope`: a list derived from the DTO widens itself the day the DTO
# widens, so it could never fail on the drift it claims to guard. Kept sorted, and
# compared sorted -- the ADR fixes *which* columns are read, not in what order.
# `document_scope_guard_statements.SCOPE_FIELD_NAMES` is the same literal from the
# usecase side.
SCOPE_COLUMNS = ["id", "owner_id"]


class DocumentStorageStatements:
    """DSL for the document storage adapter's tests."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._storage = SqlAlchemyDocumentStorage(session)
        self._accounts = SqlAlchemyAccountRepository(session)

    async def given_an_account(self) -> UUID:
        # documents.owner_id is a real FK, so a document needs a real account row.
        account = Account.create(
            id=uuid4(),
            email=f"owner-{uuid4()}@example.com",
            password_hash="hash",
            created_at=datetime.now(UTC),
        )
        await self._accounts.save(account)
        return account.id

    async def given_a_saved_document(self, owner_id: UUID, idempotency_key: str = "") -> Document:
        document = Document.create(
            owner_id=owner_id,
            document_type="эссе",
            idempotency_key=idempotency_key or f"key-{uuid4()}",
            created_at=datetime.now(UTC),
        )
        await self._storage.save_new(document)
        await self._session.commit()
        return document

    async def save_new(self, document: Document) -> None:
        await self._storage.save_new(document)

    async def find_by_id_and_owner(self, document_id: UUID, owner_id: UUID) -> Document | None:
        return await self._storage.find_by_id_and_owner(document_id, owner_id)

    async def find_scope_by_id_and_owner(
        self, document_id: UUID, owner_id: UUID
    ) -> DocumentScope | None:
        return await self._storage.find_scope_by_id_and_owner(document_id, owner_id)

    async def find_scope_of_an_absent_id(self, owner_id: UUID) -> DocumentScope | None:
        """Ask for an id that no `given_*` step ever saved.

        The id is minted here rather than in the test body so the absence is a
        property of the step, not of a `uuid4()` the reader has to trace.
        """
        return await self._storage.find_scope_by_id_and_owner(uuid4(), owner_id)

    async def find_scope_watching_what_it_reads(
        self, document_id: UUID, owner_id: UUID
    ) -> WatchedRead[DocumentScope]:
        """Run the bounded finder while watching which columns it touches.

        A separate action from the plain finder, and opt-in: only the test that
        asks what was read pays for the listener. The recorder comes back beside
        the answer rather than on a field of this class -- see `WatchedRead`.

        Why watch at all -- the whole reason this method exists next to
        `find_by_id_and_owner` is that it must not materialise `content`, and the
        returned projection cannot show whether the column was read or merely
        dropped afterwards. Only the statement can.
        """
        with recording_sql(self._session) as recorded:
            scope = await self._storage.find_scope_by_id_and_owner(document_id, owner_id)
        return WatchedRead(scope, recorded)

    def assert_scope_matches(self, actual: DocumentScope | None, expected: Document) -> None:
        assert actual is not None, (
            "the owner's own document must resolve to a scope. A port method inherited from the "
            "Protocol answers None for every input, which would refuse every user their own "
            "documents while the type checker and the usecase suite stay green."
        )
        # Structural equality on the whole frozen dataclass, not a field-by-field tuple:
        # an enumeration silently stops covering the DTO the day it grows a field, which
        # is precisely the day the bounded projection would need re-proving.
        assert actual == DocumentScope(id=expected.id, owner_id=expected.owner_id), (
            f"the scope must identify the saved document: expected "
            f"DocumentScope(id={expected.id}, owner_id={expected.owner_id}), got {actual}"
        )

    def assert_a_foreign_owners_document_is_not_resolved(
        self, actual: DocumentScope | None
    ) -> None:
        assert actual is None, (
            "another owner's document must read as absent, never resolved -- the guard's whole "
            f"premise is that the caller has no claim to that id, but the finder resolved {actual}"
        )

    def assert_an_absent_id_is_not_resolved(self, actual: DocumentScope | None) -> None:
        assert actual is None, (
            "an id that was never saved must resolve to nothing, even for an owner who does have "
            f"documents, but the finder resolved {actual}"
        )

    def assert_the_scope_was_resolved_without_reading_content(
        self, read: WatchedRead[DocumentScope], expected: Document
    ) -> None:
        """Both halves, or neither is worth anything.

        A finder that emits one cheap non-content SELECT and returns `None` would
        satisfy the projection check alone, so identity and projection are asserted
        together here rather than left to two Then steps a test could half-write.

        On the projection half: the parsed column list is the assertion, not the
        absence of a word. `"content" not in statement` is satisfiable by a
        `SELECT *`, which reads the column without ever naming it, and is spuriously
        broken by a `content_hash` column or a `WHERE`-clause mention. Comparing the
        parsed projection to the pinned column list settles both: `*` is not
        `["id", "owner_id"]`, and neither is a nine-column full-entity read.
        """
        self.assert_scope_matches(read.answer, expected)
        selected = sorted(read.recorded.selected_columns())
        assert selected == SCOPE_COLUMNS, (
            f"the scope read must select exactly {SCOPE_COLUMNS}, but selected {selected}. "
            "It answers a yes/no question and runs on every request to all seven AI-edit "
            "endpoints; reading up to 200 000 code points of `content` to answer it is the "
            f"option the ADR rejects. Statement: {read.recorded.the_only_statement()}"
        )

    async def find_by_idempotency_key(self, owner_id: UUID, key: str) -> Document | None:
        return await self._storage.find_by_idempotency_key(owner_id, key)

    async def save_content_if_version_matches(
        self, document_id: UUID, owner_id: UUID, content: str, expected_version: int
    ) -> Document | None:
        return await self._storage.save_content_if_version_matches(
            document_id=document_id,
            owner_id=owner_id,
            content=content,
            expected_version=expected_version,
            updated_at=datetime.now(UTC),
        )

    async def rollback(self) -> None:
        await self._session.rollback()

    async def commit(self) -> None:
        await self._session.commit()

    def assert_documents_match(self, actual: Document | None, expected: Document) -> None:
        assert actual is not None, "expected a document, got None"
        assert (
            actual.id,
            actual.owner_id,
            actual.document_type,
            actual.status,
            actual.content,
            actual.version,
            actual.idempotency_key,
        ) == (
            expected.id,
            expected.owner_id,
            expected.document_type,
            expected.status,
            expected.content,
            expected.version,
            expected.idempotency_key,
        ), f"stored document does not match: {actual.__dict__} != {expected.__dict__}"
