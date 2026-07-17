import asyncio
import os
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import text

from access.auth.account_storage import SqlAlchemyAccountRepository
from access.document.document_storage import SqlAlchemyDocumentStorage
from auth.account import Account
from document.document import Document
from session import create_engine, create_session_factory


class TestConcurrentSavesResolveAtomically:
    """Scenario 6.7: two same-instant saves at one version — exactly one wins.

    **Read this before trusting it: this test does NOT catch a racy implementation,
    and it is not 6.7's guard.** That is `test_document_storage_cas_shape.py`.

    It was written to separate a real CAS from the read-compare-write that
    `SqlAlchemyGenerationStorage.update()` uses, and it fails at that. Measured, not
    reasoned: that exact pattern was injected here and this test **passed**. The two
    coroutines serialized rather than interleaved — the loser's SELECT landed after
    the winner's COMMIT, read version=2, and declined on its own. The race window is
    real but narrow, so `asyncio.gather` hits it only by luck, and a test that
    reports green on the defect it names certifies the bug.

    Forcing the interleaving from outside is not possible either: the racy pattern's
    read lives *inside* the method, so there is no seam for a barrier. Hence the
    structural guard, which counts statements and is deterministic.

    What this test still earns its place for: it drives the real adapter through two
    independent sessions on separate connections against real Postgres, so it would
    catch a deadlock, an unhandled exception under concurrency, or a CAS that
    double-increments. That is a smoke test, and it is worth having — as long as
    nobody reads its green as evidence of race-safety.

    Per the amended 6.7, the two requests carry **distinct content** — with
    identical content the loser is indistinguishable from scenario 6.2's legitimate
    replay.
    """

    async def test_exactly_one_of_two_same_version_saves_wins(self):
        os.environ.setdefault("TEST_DATABASE_URL", "postgresql://textery:change-me@localhost:5432/textery")
        os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
        engine = create_engine()
        session_factory = create_session_factory(engine)

        async with session_factory() as setup_session:
            account = Account.create(
                id=uuid4(),
                email=f"race-{uuid4()}@example.com",
                password_hash="hash",
                created_at=datetime.now(timezone.utc),
            )
            await SqlAlchemyAccountRepository(setup_session).save(account)
            document = Document.create(
                owner_id=account.id,
                document_type="эссе",
                idempotency_key=f"key-{uuid4()}",
                created_at=datetime.now(timezone.utc),
            )
            await SqlAlchemyDocumentStorage(setup_session).save_new(document)
            await setup_session.commit()

        async def save(content: str):
            async with session_factory() as session:
                result = await SqlAlchemyDocumentStorage(session).save_content_if_version_matches(
                    document_id=document.id,
                    owner_id=account.id,
                    content=content,
                    expected_version=1,
                    updated_at=datetime.now(timezone.utc),
                )
                await session.commit()
                return result

        try:
            # Released together, both claiming version 1.
            first, second = await asyncio.gather(save("<p>alpha</p>"), save("<p>beta</p>"))

            winners = [outcome for outcome in (first, second) if outcome is not None]
            assert len(winners) == 1, (
                f"exactly one save must win, got {len(winners)}. Two winners means the version "
                f"check is not atomic and one client's write was silently lost."
            )
            assert winners[0].version == 2, "the winner advances the version exactly once"

            async with session_factory() as verify_session:
                stored = await SqlAlchemyDocumentStorage(verify_session).find_by_id_and_owner(
                    document.id, account.id
                )
            assert stored.version == 2, "the row must land at version 2, never 3"
            assert stored.content == winners[0].content, (
                "the stored content must be exactly the winner's — never the loser's, never interleaved"
            )
            assert stored.content in ("<p>alpha</p>", "<p>beta</p>")
        finally:
            async with engine.connect() as cleanup:
                await cleanup.execute(text("TRUNCATE TABLE generations, documents, verification_codes, accounts"))
                await cleanup.commit()
            await engine.dispose()
