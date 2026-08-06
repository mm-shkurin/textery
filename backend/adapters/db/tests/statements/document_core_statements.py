from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from access.auth.account_storage import SqlAlchemyAccountRepository
from access.document.document_storage import SqlAlchemyDocumentStorage
from auth.account import Account
from document.document import Document
from document.title_update import TitleUpdate
from statements.document_storage_assertions import DocumentStorageAssertions


class DocumentCoreStatements(DocumentStorageAssertions):
    """The arrange and act methods every document storage test uses.

    Split from `DocumentStorageStatements` (which subclasses this) when scenario
    2.1's page-settings seeds and reads carried that file past the 200-line cap.
    This half is the storage vocabulary that predates the story -- accounts,
    documents, the CAS, the session -- and the page-settings half above it is
    written in terms of it. The dependency runs one way, which is why this is the
    base: `given_a_configured_document` seeds through `given_a_saved_document`,
    and nothing here reaches upward.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__()
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

    async def find_by_id_and_owner(self, document_id: UUID, owner_id: UUID) -> Document | None:
        return await self._storage.find_by_id_and_owner(document_id, owner_id)

    async def find_by_idempotency_key(self, owner_id: UUID, key: str) -> Document | None:
        return await self._storage.find_by_idempotency_key(owner_id, key)

    async def save_content_if_version_matches(
        self,
        document_id: UUID,
        owner_id: UUID,
        content: str,
        expected_version: int,
        title: TitleUpdate,
    ) -> Document | None:
        # The signature MIRRORS the port's `title` parameter exactly -- required, no
        # default, `TitleUpdate` only -- and the value is forwarded
        # UNCHANGED -- constructing or unwrapping a TitleUpdate here would launder
        # the very thing under test. A DSL that accepted a raw `str` would let a
        # test make a call no production caller can make, and would quietly lift a
        # future `title=""` back into the `SET title = ''` shape the adapter
        # deleted by construction. `TitleUpdate.preserve()` is the content-only
        # autosave path (title omitted from the SET list), and it is spelled at
        # every call site rather than defaulted here: the port has no default, so
        # neither does its DSL mirror.
        self._last_updated_at = datetime.now(UTC)
        return await self._storage.save_content_if_version_matches(
            document_id=document_id,
            owner_id=owner_id,
            content=content,
            expected_version=expected_version,
            updated_at=self._last_updated_at,
            title=title,
        )

    async def commit(self) -> None:
        await self._session.commit()

    def expire_identity_map(self) -> None:
        """Force the next find to be a genuine SELECT, not an identity-map hit.

        The session is expire_on_commit=False, so an unexpired instance in the
        identity map is handed back with its IN-MEMORY values and a read-back
        asserts x == x. Measured, that staleness is real: holding a strong
        reference to the model and corrupting the row in raw SQL, the find returns
        the stale `''` while a find after expire_all() returns the corrupted value.

        It does NOT currently bite these tests: SQLAlchemy's identity map holds WEAK
        references, and neither `save_new` nor the CAS keeps a reference to the model
        (`model.to_domain()` is returned and the local dies), so the instance is
        collected and the map is empty by the time the find runs. That makes today's
        reads genuine by refcounting accident. This call turns the accident into a
        stated guarantee -- it costs one no-op and it is what keeps the read honest
        if anyone ever retains the model.
        """
        self._session.expire_all()
