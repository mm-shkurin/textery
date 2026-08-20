from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from access.affected_rows import affected_rows
from access.document.document_filter_sql import filter_predicates
from access.document.document_update_values import update_values
from access.keyset_pagination import paginate_by_owner
from document.document import Document
from document.document_filter import EMPTY, DocumentFilter
from document.title_update import TitleUpdate
from model.document.document_model import DocumentModel
from shared.exceptions import ConflictException
from shared.keyset_cursor import KeysetCursor


class SqlAlchemyDocumentStorage:
    """Storage adapter for manual documents.

    Every read and write filters on `owner_id` **in SQL**. No method exposes a
    document by id alone, deliberately: with the predicate baked into the query,
    a foreign document falls out as `None` structurally and no caller *can* leak
    one. A `find_by_id` sitting alongside these would be one autocomplete away
    from undoing that -- see decisions/document-ownership-decision.md.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_new(self, document: Document) -> None:
        """Insert a new document.

        Flush, never commit: the usecase owns the single commit through the
        UnitOfWork port, the convention the auth slice follows. (The generation
        adapter still self-commits; that is story-1 surface, left alone.)

        A unique violation is mapped to `ConflictException` so the calling usecase
        can recognise a replay and recover the original document. That mapping is
        the whole idempotency mechanism: the DB constraint decides, not a
        check-then-insert, so there is no TOCTOU window between the check and the
        insert.

        TWO constraints can raise it, and the exception deliberately does not say
        which: `uq_documents_owner_idempotency_key` (this owner reused a key) and
        `uq_documents_generation_id` (this generation is already a document).
        Telling them apart from here would mean reading a driver-specific
        constraint name off the wrapped error; the callers distinguish them by
        which recovery read finds a row, which is the same answer without the
        coupling. The message names both so a log line never asserts the wrong one.
        """
        self._session.add(DocumentModel.from_domain(document))
        try:
            await self._session.flush()
        except IntegrityError as error:
            raise ConflictException(
                f"document {document.id} violates a uniqueness constraint "
                f"(idempotency key {document.idempotency_key!r}, "
                f"generation {document.generation_id})"
            ) from error

    async def find_by_id_and_owner(self, document_id: UUID, owner_id: UUID) -> Document | None:
        result = await self._session.execute(
            select(DocumentModel).where(
                DocumentModel.id == document_id,
                DocumentModel.owner_id == owner_id,
            )
        )
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def find_by_idempotency_key(
        self, owner_id: UUID, idempotency_key: str
    ) -> Document | None:
        result = await self._session.execute(
            select(DocumentModel).where(
                DocumentModel.owner_id == owner_id,
                DocumentModel.idempotency_key == idempotency_key,
            )
        )
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def find_by_generation_id(self, owner_id: UUID, generation_id: UUID) -> Document | None:
        result = await self._session.execute(
            select(DocumentModel).where(
                DocumentModel.owner_id == owner_id,
                DocumentModel.generation_id == generation_id,
            )
        )
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def list_by_owner(
        self,
        owner_id: UUID,
        limit: int,
        cursor: KeysetCursor | None,
        document_filter: DocumentFilter = EMPTY,
    ) -> list[Document]:
        return [
            model.to_domain()
            for model in await paginate_by_owner(
                self._session,
                DocumentModel,
                owner_id,
                limit,
                cursor,
                filter_predicates(document_filter),
            )
        ]

    async def delete_by_id_and_owner(self, document_id: UUID, owner_id: UUID) -> bool:
        """Delete one document. Answers whether a row was actually removed.

        Owner-scoped in SQL like every other method here, and the return value is
        derived from the rowcount rather than from a preceding read: a
        read-then-delete would report success for a row a concurrent request had
        already removed, and would answer "found" for a document that vanishes
        before the DELETE lands.

        Flush, not commit — the calling usecase owns the transaction boundary.
        """
        result = await self._session.execute(
            delete(DocumentModel).where(
                DocumentModel.id == document_id,
                DocumentModel.owner_id == owner_id,
            )
        )
        await self._session.flush()
        return affected_rows(result) > 0

    async def save_content_if_version_matches(
        self,
        document_id: UUID,
        owner_id: UUID,
        content: str,
        expected_version: int,
        updated_at: datetime,
        title: TitleUpdate,
    ) -> Document | None:
        """Compare-and-swap the content. Returns the new state, or None if the
        version did not match (or the document is absent/foreign).

        **One statement.** The version is compared in the WHERE clause and the
        increment is computed in SQL; `RETURNING` hands back the new row, so there
        is no second read to race. Deliberately NOT the read-compare-write that
        `SqlAlchemyGenerationStorage.update()` uses: comparing the version in
        Python and then writing lets two concurrent sessions both read version=1,
        both pass the check, and both write version=2 -- a silently lost update
        under READ COMMITTED.

        Why this holds across processes (scenario 6.7): the loser blocks on the
        row lock, and when the winner commits Postgres re-evaluates the WHERE
        against the *updated* row, sees version=2, and matches zero rows. The
        database is the arbiter, so backend instance count is irrelevant.

        Owner and version are ANDed into one predicate: a foreign document never
        reaches the version comparison, so a correct-version guess against someone
        else's id is indistinguishable from a wrong one.
        """
        values = update_values(content, updated_at, title)
        result = await self._session.execute(
            update(DocumentModel)
            .where(
                DocumentModel.id == document_id,
                DocumentModel.owner_id == owner_id,
                DocumentModel.version == expected_version,
            )
            .values(**values)
            .returning(DocumentModel)
        )
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None
