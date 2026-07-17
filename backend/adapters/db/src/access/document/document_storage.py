from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from access.keyset_pagination import paginate_by_owner
from document.document import Document
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

        The `uq_documents_owner_idempotency_key` violation is mapped to
        `ConflictException` so the create usecase can recognise a replay and
        recover the original document. That mapping is the whole idempotency
        mechanism: the DB constraint decides, not a check-then-insert, so there is
        no TOCTOU window between the check and the insert.
        """
        self._session.add(DocumentModel.from_domain(document))
        try:
            await self._session.flush()
        except IntegrityError as error:
            raise ConflictException(
                f"document with idempotency key {document.idempotency_key} already exists"
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

    async def list_by_owner(
        self, owner_id: UUID, limit: int, cursor: KeysetCursor | None
    ) -> list[Document]:
        return [
            model.to_domain()
            for model in await paginate_by_owner(
                self._session, DocumentModel, owner_id, limit, cursor
            )
        ]

    async def save_content_if_version_matches(
        self,
        document_id: UUID,
        owner_id: UUID,
        content: str,
        expected_version: int,
        updated_at: datetime,
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
        result = await self._session.execute(
            update(DocumentModel)
            .where(
                DocumentModel.id == document_id,
                DocumentModel.owner_id == owner_id,
                DocumentModel.version == expected_version,
            )
            .values(
                content=content,
                version=DocumentModel.version + 1,
                updated_at=updated_at,
            )
            .returning(DocumentModel)
        )
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None
