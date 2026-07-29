from datetime import UTC, datetime
from uuid import uuid4

from access.auth.account_storage import SqlAlchemyAccountRepository
from access.document.document_storage import SqlAlchemyDocumentStorage
from auth.account import Account
from document.document import Document
from session import create_engine, create_session_factory
from statements.cas_shape_statements import assert_is_a_single_compare_and_swap
from statements.database_cleanup import truncate_all
from statements.database_url import configure_test_database_url
from statements.sql_recorder import recording_sql


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
        configure_test_database_url()
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

        try:
            async with session_factory() as session:
                storage = SqlAlchemyDocumentStorage(session)
                with recording_sql(session) as recorded:
                    await storage.save_content_if_version_matches(
                        document_id=document.id,
                        owner_id=account.id,
                        content="<p>x</p>",
                        expected_version=1,
                        updated_at=datetime.now(UTC),
                    )

            assert_is_a_single_compare_and_swap(
                recorded,
                "save_content_if_version_matches must not SELECT. A read before the write is "
                "the read-compare-write pattern that loses concurrent updates.",
            )
        finally:
            await truncate_all(engine)
            await engine.dispose()
