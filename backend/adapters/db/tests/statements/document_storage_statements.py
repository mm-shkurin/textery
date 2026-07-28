from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from access.auth.account_storage import SqlAlchemyAccountRepository
from access.document.document_storage import SqlAlchemyDocumentStorage
from auth.account import Account
from document.document import Document
from document.title_update import TitleUpdate


class DocumentStorageStatements:
    """DSL for the document storage adapter's tests."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._storage = SqlAlchemyDocumentStorage(session)
        self._accounts = SqlAlchemyAccountRepository(session)
        # The clock the DSL hands the CAS. Captured so `updated_at` -- the fourth
        # column the SET list writes -- can be asserted against the exact value that
        # went in, rather than left unpinned or waved through with a monotonicity check.
        self._last_updated_at: datetime | None = None

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
        title: TitleUpdate | str | None = None,
    ) -> Document | None:
        # One adapter method, one DSL method. The value is forwarded UNCHANGED --
        # unwrapping a TitleUpdate here would launder the very thing under test and
        # make the VO cases vacuous. `title=None` and `TitleUpdate.preserve()` are
        # both the content-only autosave path (title omitted from the SET list).
        # The raw `str` arm is transitional; `green-adapter db (TitleUpdate unwrap)`
        # owns its removal from production.
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
        self,
        actual: Document | None,
        original: Document,
        *,
        title: str | None,
        content: str,
        version: int,
    ) -> None:
        """Assert the full post-CAS row: what the save changed AND what it must not.

        A title assertion alone is satisfiable by a save that wrote the title but
        dropped the content, and -- on the preserve-on-omit path -- by a CAS that
        matched zero rows and did nothing at all. Pinning the version is what makes
        "the save actually happened" observable.

        The CAS SET list writes FOUR columns (content, version, updated_at, and
        conditionally title). Pinning three of them left `updated_at` unverified in
        every test using this method: a CAS that dropped it from the SET list, or
        wrote the wrong clock, stayed green. It is asserted against the exact value
        the DSL generated for the last save -- category 2 "capturable from setup",
        not a monotonicity bound, because the DSL owns that clock and knows it.

        The six columns the CAS must NOT touch are pinned against the pre-save
        document, so an over-broad SET list (a clobbered `created_at`, a reset
        `status`) is observable rather than invisible.
        """
        assert actual is not None, "expected a stored document, got None"
        assert self._last_updated_at is not None, (
            "assert_stored_state requires a preceding save_content_if_version_matches"
        )
        expected = Document.reconstitute(
            id=original.id,
            owner_id=original.owner_id,
            document_type=original.document_type,
            status=original.status,
            idempotency_key=original.idempotency_key,
            created_at=original.created_at,
            title=title,
            content=content,
            version=version,
            updated_at=self._last_updated_at,
        )
        self.assert_documents_match(actual, expected)
