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
        increment computed in SQL, with RETURNING handing back the new row.

        This was a read-compare-write: `session.get`, compare `model.version` to
        `generation.version` in Python, then assign and commit. That check cannot
        hold under READ COMMITTED -- two sessions both read version=1, both pass
        the comparison, and both write version=2, so one update is silently lost
        and the ConflictException it should have raised never fires. It matters
        here specifically because the stale sweep runs in every replica's
        lifespan: two instances sweeping the same stranded row both reached this
        method, and the guard that was supposed to stop the second one was the
        broken one.

        `SqlAlchemyDocumentStorage.save_content_if_version_matches` already does
        it this way and its docstring names this method as the counter-example.
        This closes that gap rather than leaving the two adapters disagreeing
        about how optimistic locking works.

        Why it holds across processes: the loser blocks on the row lock, and when
        the winner commits Postgres re-evaluates the WHERE against the updated
        row, sees the bumped version, and matches zero rows. The database is the
        arbiter, so the instance count is irrelevant.

        Zero rows matched is ambiguous on its own -- absent or version-mismatched
        -- so the caller's two distinct exceptions need one follow-up read to tell
        which. That read is off the happy path and only runs when the write has
        already failed.
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
