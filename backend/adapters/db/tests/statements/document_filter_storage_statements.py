"""DSL for the filtered history read and the delete, against a real Postgres.

Separate from `HistoryPagingStatements` because the claims are different: that one
is about the keyset walk both storages share, this one is about SQL only the
document storage has -- an `ILIKE` whose wildcards must be escaped, a date window
whose ends are inclusive, and a `DELETE` whose rowcount is the answer.

None of it can be proved against the in-memory fake. The fake matches with a
Python `in`, which has no wildcards to escape and no notion of a rowcount -- so an
unescaped `%` would pass every usecase test and match the caller's whole history
the moment it reached the database.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from access.auth.account_storage import SqlAlchemyAccountRepository
from access.document.document_storage import SqlAlchemyDocumentStorage
from auth.account import Account
from document.document import Document
from document.document_filter import DocumentFilter

BASE_TIME = datetime(2026, 8, 20, 12, 0, tzinfo=UTC)


class DocumentFilterStorageStatements:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._accounts = SqlAlchemyAccountRepository(session)
        self._documents = SqlAlchemyDocumentStorage(session)
        self.page: list[Document] = []
        self.deleted: bool | None = None

    async def given_an_account(self) -> UUID:
        account = Account.create(
            id=uuid4(),
            email=f"owner-{uuid4()}@example.com",
            password_hash="hash",
            created_at=datetime.now(UTC),
        )
        await self._accounts.save(account)
        return account.id

    async def given_a_document(
        self,
        owner_id: UUID,
        title: str | None = None,
        content: str = "",
        days_old: int = 0,
    ) -> Document:
        stamp = BASE_TIME - timedelta(days=days_old)
        document = Document(
            id=uuid4(),
            owner_id=owner_id,
            document_type="доклад",
            status="draft",
            content=content,
            version=1,
            idempotency_key=str(uuid4()),
            created_at=stamp,
            updated_at=stamp,
            title=title,
        )
        await self._documents.save_new(document)
        await self._session.commit()
        return document

    async def list_filtered(self, owner_id: UUID, **filter_kwargs: str) -> None:
        self.page = await self._documents.list_by_owner(
            owner_id, 20, None, DocumentFilter.parse(**filter_kwargs)
        )

    async def delete(self, document_id: UUID, owner_id: UUID) -> None:
        self.deleted = await self._documents.delete_by_id_and_owner(document_id, owner_id)
        await self._session.commit()

    async def count_for(self, owner_id: UUID) -> int:
        return len(await self._documents.list_by_owner(owner_id, 20, None))

    def assert_page_ids(self, *expected: Document) -> None:
        assert [row.id for row in self.page] == [document.id for document in expected], (
            f"page held {[row.title for row in self.page]}"
        )

    def assert_page_is_empty(self) -> None:
        assert self.page == [], f"expected no matches, got {[row.title for row in self.page]}"
