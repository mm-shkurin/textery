"""Engine + seeded generation for the generation tests that own their engine.

Most of this suite gets a session from a conftest fixture. The CAS-shape and staleness
tests cannot: they attach a statement recorder or drive several independent sessions
against one engine, so they build the engine themselves. This is the arrange step they
share, in one place rather than one copy per module.
"""

from datetime import UTC, datetime
from uuid import uuid4

from access.auth.account_storage import SqlAlchemyAccountRepository
from access.generation.generation_storage import SqlAlchemyGenerationStorage
from auth.account import Account
from generation.generation import Generation
from session import create_engine
from statements.database_url import configure_test_database_url


def generation_test_engine():
    """A fresh engine pointed at the test database. Callers must `dispose()` it."""
    configure_test_database_url()
    return create_engine()


async def seed_account_and_generation(session_factory) -> tuple[Account, Generation]:
    """One committed account and one saved generation belonging to it."""
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
