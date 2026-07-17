import os
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import event, text

from access.auth.account_storage import SqlAlchemyAccountRepository
from access.document.document_storage import SqlAlchemyDocumentStorage
from auth.account import Account
from document.document import Document
from session import create_engine, create_session_factory


class TestSaveIsASingleCompareAndSwapStatement:
    """Scenario 6.7's real guard: the version is compared in SQL, not in Python.

    Why this test and not a concurrency test: a two-session `asyncio.gather` race
    **cannot** catch the defect. Verified, not assumed -- the read-compare-write
    pattern from `SqlAlchemyGenerationStorage.update()` was injected here and the
    gather-based test passed, because the two coroutines happened to serialize: the
    loser's SELECT landed after the winner's COMMIT, read version=2, and bailed on
    its own. The race window is real but narrow and timing-dependent, so that test
    is a coin flip reporting green.

    Nor can the interleaving be forced from outside: the racy pattern's read lives
    *inside* the method, and there is no seam to inject a barrier into. A test that
    cannot fail on the defect it names is worse than no test -- it certifies the bug.

    So the guard is structural, and it pins the decision itself
    (decisions/document-ownership-decision.md, and the CAS docstring): the compare
    and the increment happen in **one** statement. A read-compare-write emits a
    SELECT first; a CAS does not. Counting statements catches the substitution
    deterministically, on every run, with no timing dependence.
    """

    async def test_should_emit_one_update_and_never_read_first(self):
        os.environ.setdefault(
            "TEST_DATABASE_URL", "postgresql://textery:change-me@localhost:5432/textery"
        )
        os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
        engine = create_engine()
        session_factory = create_session_factory(engine)

        async with session_factory() as setup:
            account = Account.create(
                id=uuid4(),
                email=f"shape-{uuid4()}@example.com",
                password_hash="hash",
                created_at=datetime.now(UTC),
            )
            await SqlAlchemyAccountRepository(setup).save(account)
            document = Document.create(
                owner_id=account.id,
                document_type="эссе",
                idempotency_key=f"key-{uuid4()}",
                created_at=datetime.now(UTC),
            )
            await SqlAlchemyDocumentStorage(setup).save_new(document)
            await setup.commit()

        captured: list[str] = []

        def record(conn, cursor, statement, parameters, context, executemany):
            captured.append(" ".join(statement.split()).upper())

        try:
            async with session_factory() as session:
                storage = SqlAlchemyDocumentStorage(session)
                event.listen(engine.sync_engine, "before_cursor_execute", record)
                try:
                    await storage.save_content_if_version_matches(
                        document_id=document.id,
                        owner_id=account.id,
                        content="<p>x</p>",
                        expected_version=1,
                        updated_at=datetime.now(UTC),
                    )
                finally:
                    event.remove(engine.sync_engine, "before_cursor_execute", record)

            selects = [sql for sql in captured if sql.startswith("SELECT")]
            updates = [sql for sql in captured if sql.startswith("UPDATE")]

            assert selects == [], (
                "save_content_if_version_matches must not SELECT. A read before the write is the "
                f"read-compare-write pattern that loses concurrent updates. Got: {selects}"
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
            async with engine.connect() as cleanup:
                await cleanup.execute(
                    text("TRUNCATE TABLE generations, documents, verification_codes, accounts")
                )
                await cleanup.commit()
            await engine.dispose()
