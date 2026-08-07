from uuid import uuid4

import pytest
from sqlalchemy import event

from access.generation.generation_storage import SqlAlchemyGenerationStorage
from generation.generation import Generation
from session import create_session_factory
from shared.exceptions import ConflictException, NotFoundException
from statements.generation_engine_fixtures import generation_test_engine, seed, truncate


class TestUpdateIsASingleCompareAndSwapStatement:
    """`update()` compares the version in SQL, not in Python.

    This mirrors `test_document_storage_cas_shape.py`, deliberately and for the
    reason that file spells out: a two-session `asyncio.gather` race cannot catch
    a read-compare-write, because the coroutines serialize and the loser's SELECT
    lands after the winner's COMMIT, reads the bumped version, and declines on its
    own. A test that reports green on the defect it names certifies the bug.

    So the guard is structural. A read-compare-write emits a SELECT before the
    write; a CAS does not. Counting statements catches the substitution on every
    run with no timing dependence.

    This method was the read-compare-write -- the document CAS's own docstring
    cited it by name as the counter-example. It matters here more than for
    documents: the stale sweep runs in every replica's lifespan, so two instances
    can reach this method for the same stranded row, and the guard meant to stop
    the second one was the broken one.
    """

    async def test_should_emit_one_update_and_never_read_first(self):
        engine = generation_test_engine()
        session_factory = create_session_factory(engine)
        _, generation = await seed(session_factory)

        captured: list[str] = []

        def record(conn, cursor, statement, parameters, context, executemany):
            captured.append(" ".join(statement.split()).upper())

        try:
            generation.complete("Готовый доклад")
            async with session_factory() as session:
                storage = SqlAlchemyGenerationStorage(session)
                event.listen(engine.sync_engine, "before_cursor_execute", record)
                try:
                    await storage.update(generation)
                finally:
                    event.remove(engine.sync_engine, "before_cursor_execute", record)

            selects = [sql for sql in captured if sql.startswith("SELECT")]
            updates = [sql for sql in captured if sql.startswith("UPDATE")]

            assert selects == [], (
                "update() must not SELECT before writing. A read-compare-write lets two "
                "sessions both read version=1, both pass the check, and both write version=2 "
                f"-- one update silently lost. Got: {selects}"
            )
            assert len(updates) == 1, f"expected exactly one UPDATE, got {len(updates)}: {updates}"

            statement = updates[0]
            assert "VERSION =" in statement.split("WHERE", 1)[1], (
                f"the version must be compared in the WHERE clause, not in Python. Got: {statement}"
            )
            assert "RETURNING" in statement, (
                "the new row must come back from the same statement; a follow-up SELECT would "
                f"re-open the race the CAS closes. Got: {statement}"
            )
        finally:
            await truncate(engine)
            await engine.dispose()


class TestUpdateStillReportsTheTwoFailures:
    """Collapsing to one statement must not blur absent and version-mismatched.

    Zero rows matched is ambiguous, so the adapter re-reads to tell the two apart.
    These pin that the distinction survived the rewrite -- the sweep and the
    request path both rely on ConflictException meaning "someone else got there".
    """

    async def test_should_raise_conflict_when_the_version_moved_on(self):
        engine = generation_test_engine()
        session_factory = create_session_factory(engine)
        _, generation = await seed(session_factory)

        try:
            generation.complete("first")
            async with session_factory() as session:
                await SqlAlchemyGenerationStorage(session).update(generation)

            # A second writer still holding the pre-update version, exactly as a
            # second replica's sweep would.
            stale = Generation.create(
                owner_id=generation.owner_id,
                topic="Космос",
                volume_pages=3,
                requirements=None,
                extra_wishes=None,
                document_type="доклад",
            )
            stale.id = generation.id
            stale.version = 1
            stale.complete("second")

            with pytest.raises(ConflictException):
                async with session_factory() as session:
                    await SqlAlchemyGenerationStorage(session).update(stale)

            async with session_factory() as verify:
                stored = await SqlAlchemyGenerationStorage(verify).get_by_id_and_owner(
                    generation.id, generation.owner_id
                )
            assert stored.version == 2, f"the row must land at version 2, got {stored.version}"
            assert stored.content == "first", (
                f"the first writer's content must survive, got {stored.content!r}"
            )
        finally:
            await truncate(engine)
            await engine.dispose()

    async def test_should_raise_not_found_when_the_row_is_gone(self):
        engine = generation_test_engine()
        session_factory = create_session_factory(engine)

        try:
            absent = Generation.create(
                owner_id=uuid4(),
                topic="Космос",
                volume_pages=3,
                requirements=None,
                extra_wishes=None,
                document_type="доклад",
            )
            absent.complete("x")

            with pytest.raises(NotFoundException):
                async with session_factory() as session:
                    await SqlAlchemyGenerationStorage(session).update(absent)
        finally:
            await truncate(engine)
            await engine.dispose()
