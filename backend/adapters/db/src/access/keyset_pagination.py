from uuid import UUID

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from shared.keyset_cursor import KeysetCursor


async def paginate_by_owner(
    session: AsyncSession,
    model,
    owner_id: UUID,
    limit: int,
    cursor: KeysetCursor | None,
) -> list:
    """One page of `model` rows owned by `owner_id`, newest first.

    Shared by the generation and document storages: the SQL is identical bar the
    table, and two copies of a keyset predicate is exactly how one of them ends up
    silently missing its owner filter.

    The seek predicate is a **row-value comparison** -- `(created_at, id) < (:t, :i)`
    -- not `created_at < :t OR (created_at = :t AND id < :i)`. The two are logically
    equal, but Postgres can drive an index scan straight from a row-value compare,
    while the OR-expansion typically degrades into a filter. Both spellings are
    correct; only one stays O(page).

    `<`, and DESC on both columns, so paging walks backwards through history from
    newest to oldest. The tuple ordering must mirror the tuple in the predicate or
    the seek lands in the wrong place -- and must mirror the composite index, or
    the scan it exists for never happens.
    """
    statement = select(model).where(model.owner_id == owner_id)
    if cursor is not None:
        statement = statement.where(
            tuple_(model.created_at, model.id) < tuple_(cursor.created_at, cursor.id)
        )
    statement = statement.order_by(model.created_at.desc(), model.id.desc()).limit(limit)
    result = await session.execute(statement)
    return list(result.scalars().all())
