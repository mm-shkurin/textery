"""The staleness half of the generation-storage shape tests.

Split from `test_generation_storage_cas_shape.py`, which had grown past the
200-line limit. The two halves ask different questions of the same table -- one
about how `update` is issued, one about which rows the sweep selects -- and share
only the engine/seed helpers, which now live in
`statements.generation_engine_fixtures`.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from access.generation.generation_storage import SqlAlchemyGenerationStorage
from session import create_session_factory
from statements.generation_engine_fixtures import generation_test_engine, seed, truncate


class TestStalenessMeansStalledNotOld:
    """The sweep asks when a row last made progress, not when it was created.

    created_at never changes, so requeueing a stale row left it stale: it matched
    the next sweep, and every sweep after that, each one re-triggering a paid
    provider call. At the shipped 60-second interval that is one paid call per
    minute per stuck row, indefinitely.
    """

    async def test_should_not_return_a_row_again_once_it_has_been_requeued(self):
        engine = generation_test_engine()
        session_factory = create_session_factory(engine)
        _, generation = await seed(session_factory)

        try:
            # Age the row as a worker that died 20 minutes ago would leave it.
            stalled_since = datetime.now(UTC) - timedelta(minutes=20)
            async with engine.connect() as conn:
                await conn.execute(
                    text("UPDATE generations SET created_at = :t, updated_at = :t WHERE id = :i"),
                    {"t": stalled_since, "i": generation.id},
                )
                await conn.commit()

            async def sweep() -> int:
                older_than = datetime.now(UTC) - timedelta(minutes=10)
                async with session_factory() as session:
                    storage = SqlAlchemyGenerationStorage(session)
                    stale = await storage.list_stale(older_than)
                    for row in stale:
                        row.requeue()
                        await storage.update(row)
                    return len(stale)

            assert await sweep() == 1, "the stalled row must be picked up once"
            assert await sweep() == 0, (
                "the requeued row must not be stale again -- on created_at it was, "
                "so every sweep re-triggered it and paid for another provider call"
            )
            assert await sweep() == 0
        finally:
            await truncate(engine)
            await engine.dispose()

    async def test_should_still_pick_up_a_row_that_stalls_again(self):
        """The requeue buys one interval, not immunity."""
        engine = generation_test_engine()
        session_factory = create_session_factory(engine)
        _, generation = await seed(session_factory)

        try:
            async with engine.connect() as conn:
                await conn.execute(
                    text("UPDATE generations SET updated_at = :t WHERE id = :i"),
                    {"t": datetime.now(UTC) - timedelta(minutes=20), "i": generation.id},
                )
                await conn.commit()

            async with session_factory() as session:
                assert (
                    len(
                        await SqlAlchemyGenerationStorage(session).list_stale(
                            datetime.now(UTC) - timedelta(minutes=10)
                        )
                    )
                    == 1
                )

            # Time passes again with no progress: it is stale once more.
            async with engine.connect() as conn:
                await conn.execute(
                    text("UPDATE generations SET updated_at = :t WHERE id = :i"),
                    {"t": datetime.now(UTC) - timedelta(minutes=11), "i": generation.id},
                )
                await conn.commit()

            async with session_factory() as session:
                assert (
                    len(
                        await SqlAlchemyGenerationStorage(session).list_stale(
                            datetime.now(UTC) - timedelta(minutes=10)
                        )
                    )
                    == 1
                ), "a row that stalls again must be recoverable again"
        finally:
            await truncate(engine)
            await engine.dispose()
