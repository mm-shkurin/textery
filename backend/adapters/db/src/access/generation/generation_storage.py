from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from access.keyset_pagination import paginate_by_owner
from generation.generation import IN_PROGRESS_STATUS, PENDING_STATUS, Generation
from model.generation.generation_model import GenerationModel
from shared.exceptions import ConflictException, NotFoundException
from shared.keyset_cursor import KeysetCursor


class SqlAlchemyGenerationStorage:
    """Storage adapter for generations.

    There is deliberately no `get(id)`: the only by-id read filters on `owner_id`
    **in SQL**, so a foreign generation falls out as `None` structurally rather
    than relying on every caller remembering an ownership `if`. A `get(id)` sitting
    alongside `get_by_id_and_owner` would be one autocomplete away from undoing
    that -- the same reasoning as `SqlAlchemyDocumentStorage`, see
    decisions/document-ownership-decision.md.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, generation: Generation) -> None:
        self._session.add(GenerationModel.from_domain(generation))
        await self._session.commit()

    async def get_by_id_and_owner(self, generation_id: UUID, owner_id: UUID) -> Generation | None:
        result = await self._session.execute(
            select(GenerationModel).where(
                GenerationModel.id == generation_id,
                GenerationModel.owner_id == owner_id,
            )
        )
        model = result.scalar_one_or_none()
        return model.to_domain() if model is not None else None

    async def update(self, generation: Generation) -> None:
        """Compare-and-swap the generation's state on its version.

        **One statement.** The version is compared in the WHERE clause and the
        increment computed in SQL; RETURNING hands back the new row. Comparing the
        version in Python and then writing would let two sessions both read
        version=1, both pass the check, and both write version=2 -- a silently
        lost update under READ COMMITTED. The stale sweep runs in every replica,
        so two instances do reach this method for the same row.

        Why it holds across processes: the loser blocks on the row lock, and when
        the winner commits Postgres re-evaluates the WHERE against the updated
        row, sees the bumped version, and matches zero rows. The database is the
        arbiter, so the instance count is irrelevant.

        Zero rows matched is ambiguous -- absent or version-mismatched -- and
        callers need those as different exceptions, so one follow-up read decides
        which. It runs only when the write has already failed.

        Same shape as `SqlAlchemyDocumentStorage.save_content_if_version_matches`;
        `test_generation_storage_cas_shape.py` pins it, since a concurrency test
        cannot (see that file).
        """
        result = await self._session.execute(
            update(GenerationModel)
            .where(
                GenerationModel.id == generation.id,
                GenerationModel.version == generation.version,
            )
            .values(
                status=generation.status,
                content=generation.content,
                error_message=generation.error_message,
                version=GenerationModel.version + 1,
            )
            .returning(GenerationModel)
        )
        model = result.scalar_one_or_none()
        if model is None:
            await self._session.rollback()
            raise await self._explain_failed_update(generation)
        await self._session.commit()
        generation.version = model.version

    async def _explain_failed_update(self, generation: Generation) -> Exception:
        """Decide which error a zero-row UPDATE meant. Failure path only."""
        exists = await self._session.execute(
            select(GenerationModel.id).where(GenerationModel.id == generation.id)
        )
        if exists.scalar_one_or_none() is None:
            return NotFoundException(f"generation {generation.id} not found")
        return ConflictException(f"generation {generation.id} was concurrently modified")

    async def list_by_owner(
        self, owner_id: UUID, limit: int, cursor: KeysetCursor | None
    ) -> list[Generation]:
        return [
            model.to_domain()
            for model in await paginate_by_owner(
                self._session, GenerationModel, owner_id, limit, cursor
            )
        ]

    async def list_stale(self, older_than: datetime) -> list[Generation]:
        stmt = select(GenerationModel).where(
            GenerationModel.status.in_((PENDING_STATUS, IN_PROGRESS_STATUS)),
            GenerationModel.created_at < older_than,
        )
        result = await self._session.execute(stmt)
        return [model.to_domain() for model in result.scalars().all()]
