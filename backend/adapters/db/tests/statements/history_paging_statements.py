from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from access.auth.account_storage import SqlAlchemyAccountRepository
from access.document.document_storage import SqlAlchemyDocumentStorage
from access.generation.generation_storage import SqlAlchemyGenerationStorage
from auth.account import Account
from document.document import Document
from generation.generation import Generation
from shared.keyset_cursor import KeysetCursor

BASE_TIME = datetime(2026, 7, 17, 12, 0, 0, tzinfo=timezone.utc)


class HistoryPagingStatements:
    """DSL for the owner-scoped keyset history reads.

    Drives generations and documents through one surface: both storages implement
    the same `list_by_owner(owner_id, limit, cursor)` contract, so the paging
    behaviour under test is identical and asserting it twice by hand would let the
    two drift.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._accounts = SqlAlchemyAccountRepository(session)
        self._generations = SqlAlchemyGenerationStorage(session)
        self._documents = SqlAlchemyDocumentStorage(session)
        self.page: list = []

    async def given_an_account(self) -> UUID:
        account = Account.create(
            id=uuid4(),
            email=f"owner-{uuid4()}@example.com",
            password_hash="hash",
            created_at=datetime.now(timezone.utc),
        )
        await self._accounts.save(account)
        return account.id

    async def given_a_generation(
        self, owner_id: UUID, created_at: Optional[datetime] = None
    ) -> Generation:
        generation = Generation(
            id=uuid4(),
            owner_id=owner_id,
            status="completed",
            created_at=created_at or datetime.now(timezone.utc),
            topic="Как работает фотосинтез",
            volume_pages=3,
            requirements=None,
            extra_wishes=None,
            document_type="доклад",
            content="Готовый доклад",
        )
        await self._generations.save(generation)
        return generation

    async def given_a_document(
        self, owner_id: UUID, created_at: Optional[datetime] = None
    ) -> Document:
        stamp = created_at or datetime.now(timezone.utc)
        document = Document(
            id=uuid4(),
            owner_id=owner_id,
            document_type="доклад",
            status="draft",
            content="",
            version=1,
            idempotency_key=str(uuid4()),
            created_at=stamp,
            updated_at=stamp,
        )
        await self._documents.save_new(document)
        await self._session.commit()
        return document

    async def given_generations_seconds_apart(self, owner_id: UUID, count: int) -> list[Generation]:
        """`count` generations, newest first in the returned list.

        Timestamps are explicit and descending rather than "whatever now() gave":
        the assertions are about ordering, so the fixture must not depend on how
        fast the inserts happened to run.
        """
        return [
            await self.given_a_generation(owner_id, created_at=BASE_TIME - timedelta(seconds=index))
            for index in range(count)
        ]

    async def list_generations(
        self, owner_id: UUID, limit: int, cursor: Optional[KeysetCursor] = None
    ) -> None:
        self.page = await self._generations.list_by_owner(owner_id, limit, cursor)

    async def list_documents(
        self, owner_id: UUID, limit: int, cursor: Optional[KeysetCursor] = None
    ) -> None:
        self.page = await self._documents.list_by_owner(owner_id, limit, cursor)

    def cursor_after_last_of_page(self) -> KeysetCursor:
        return KeysetCursor.of(self.page[-1])

    def assert_page_ids(self, *expected) -> None:
        actual_ids = [row.id for row in self.page]
        expected_ids = [row.id for row in expected]
        assert actual_ids == expected_ids, (
            f"expected page ids {expected_ids} in this exact order, got {actual_ids}"
        )

    def assert_page_is_empty(self) -> None:
        assert self.page == [], f"expected an empty page, got {[row.id for row in self.page]}"
