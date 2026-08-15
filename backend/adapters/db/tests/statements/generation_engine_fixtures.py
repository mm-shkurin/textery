"""Engine, seed and teardown for the generation-storage tests that hit Postgres.

Extracted when `test_generation_storage_cas_shape.py` outgrew the 200-line limit
and had to become two files. These three helpers were what both halves needed, so
they live here rather than being copied into each -- a copied `_seed` is how the
two halves start seeding subtly different rows and stop being comparable.
"""

from datetime import UTC, datetime
from uuid import uuid4

from access.auth.account_storage import SqlAlchemyAccountRepository
from access.generation.generation_storage import SqlAlchemyGenerationStorage
from auth.account import Account
from generation.generation import Generation
from session import create_engine
from statements.database_cleanup import truncate_all
from statements.database_url import resolve_test_database_url


def generation_test_engine():
    """The engine, pointed at the test database through the guarded resolver.

    It used to resolve the URL itself, with its own `setdefault` defaulting to
    `.../textery` -- the *application's* database, not `textery_test`. `truncate`
    below empties every table, so on a developer machine with no TEST_DATABASE_URL
    set, these tests wiped the local stack. That is not hypothetical: it is the
    2026-08-06 incident `statements/database_url.py` documents, and the guard
    added there in response was the one thing this file was not going through.
    """
    resolve_test_database_url()
    return create_engine()


async def seed(session_factory) -> tuple[Account, Generation]:
    """One account and one pending generation belonging to it.

    The account is created with a unique email per call, so tests that run against
    a database another test already touched do not collide on the unique index.
    """
    async with session_factory() as setup:
        account = Account.create(
            id=uuid4(),
            email=f"gen-shape-{uuid4()}@example.com",
            password_hash="hash",
            created_at=datetime.now(UTC),
        )
        await SqlAlchemyAccountRepository(setup).save(account)
        await setup.commit()
    generation = Generation.create(
        owner_id=account.id,
        topic="Космос",
        volume_pages=3,
        requirements=None,
        extra_wishes=None,
        document_type="доклад",
    )
    async with session_factory() as setup:
        await SqlAlchemyGenerationStorage(setup).save(generation)
    return account, generation


async def truncate(engine) -> None:
    await truncate_all(engine)
