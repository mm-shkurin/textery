from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from access.auth.account_storage import SqlAlchemyAccountRepository
from access.document.document_storage import SqlAlchemyDocumentStorage
from auth.account import Account
from document.document import Document


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
        title: str | None = None,
    ) -> Document | None:
        # One adapter method, one DSL method. `title=None` is the content-only
        # autosave path (title omitted from the SET list, never wiped to NULL).
        return await self._storage.save_content_if_version_matches(
            document_id=document_id,
            owner_id=owner_id,
            content=content,
            expected_version=expected_version,
            updated_at=datetime.now(UTC),
            title=title,
        )

    async def commit(self) -> None:
        await self._session.commit()

    def expire_identity_map(self) -> None:
        # The session is built with expire_on_commit=False, and the CAS UPDATE's
        # RETURNING loads the row into the identity map -- so a plain find after a
        # save would hand back that cached instance, never re-hydrating from a real
        # SELECT. expire_all() drops the cache so the next find issues a genuine
        # SELECT, exercising the read path a separate export/get request would take.
        self._session.expire_all()

    def assert_documents_match(self, actual: Document | None, expected: Document) -> None:
        assert actual is not None, "expected a document, got None"
        # Every persisted field, so a column that silently fails to round-trip
        # (as `title` did before it was listed here) cannot hide behind a subset.
        assert (
            actual.id,
            actual.owner_id,
            actual.document_type,
            actual.status,
            actual.title,
            actual.content,
            actual.version,
            actual.idempotency_key,
            actual.created_at,
            actual.updated_at,
        ) == (
            expected.id,
            expected.owner_id,
            expected.document_type,
            expected.status,
            expected.title,
            expected.content,
            expected.version,
            expected.idempotency_key,
            expected.created_at,
            expected.updated_at,
        ), f"stored document does not match: {actual.__dict__} != {expected.__dict__}"

    def assert_stored_state(
        self, actual: Document | None, *, title: str | None, content: str, version: int
    ) -> None:
        """Assert the full post-CAS state, not just the field under test.

        A title assertion alone is satisfiable by a save that wrote the title but
        dropped the content, and -- on the preserve-on-omit path -- by a CAS that
        matched zero rows and did nothing at all. Pinning the version is what makes
        "the save actually happened" observable.
        """
        assert actual is not None, "expected a stored document, got None"
        assert (actual.title, actual.content, actual.version) == (title, content, version), (
            f"stored state does not match: title={actual.title!r} content={actual.content!r} "
            f"version={actual.version} != title={title!r} content={content!r} version={version}"
        )
