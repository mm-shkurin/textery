from uuid import UUID

from document_edit.ai_edit_scope import AiEditScope
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from model.document_edit.ai_edit_model import AiEditModel


class SqlAlchemyAiEditStorage:
    """Storage adapter for AI edits.

    Satisfies `AiEditRepository` structurally, as `SqlAlchemyDocumentStorage` does
    for `DocumentRepository` -- inheriting the Protocol would turn every
    unimplemented method into a concrete body that answers `None`.

    There is deliberately no finder by edit id alone: the path document id is
    authoritative, so the edit is only ever looked up together with the document it
    must belong to.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_scope_by_id_and_document(
        self, *, edit_id: UUID, document_id: UUID
    ) -> AiEditScope | None:
        """The document-scoped existence check, without the edit body.

        Projects the two scope columns in SQL rather than reading the entity and
        slicing it in Python: the two look identical in the return value, and this
        runs on the guard path of all three edit-id-carrying endpoints, where a
        full-entity read would carry the instruction and the generated content
        with it.

        Both ids are predicates, so an edit of another document falls out as
        `None` in SQL -- indistinguishable from an absent one, which is exactly
        what the caller renders.

        The ids are keyword-only: two same-typed UUIDs in a row transpose
        silently, and on the one method whose entire job is scoping that is an
        authorization defect that never reaches a stack trace.
        """
        result = await self._session.execute(
            select(AiEditModel.id, AiEditModel.document_id).where(
                AiEditModel.id == edit_id,
                AiEditModel.document_id == document_id,
            )
        )
        row = result.one_or_none()
        return AiEditScope(id=row.id, document_id=row.document_id) if row else None
