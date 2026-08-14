from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import event

from access.auth.account_storage import SqlAlchemyAccountRepository
from access.auth.avatar_storage import SqlAlchemyAvatarRepository
from auth.account import Account
from session import create_session_factory
from statements.generation_engine_fixtures import generation_test_engine, truncate

AVATAR_BYTES_COLUMN = "AVATAR_BYTES"


class TestProfileReadNeverSelectsTheAvatarBytes:
    """`GET /me` reads the profile without loading the image.

    This is the most expensive mistake available in this story, and it is silent:
    every assertion about the profile still passes with `avatar_bytes` in the
    SELECT. The endpoint runs on EVERY authenticated page view -- it is the
    highest-rate query in the product -- so an eagerly mapped `bytea` adds the
    whole image to every one of those responses' database traffic, on the account
    with the largest avatar first.

    The guard has to be structural, because no behavioural test can see it. The
    column is mapped `deferred=True`, and this captures the statements the profile
    read actually emits and asserts the column is not among them. It catches both
    ways the arrangement can be lost: `deferred` removed from the mapping, and a
    `to_domain` that reads `self.avatar_bytes` and so triggers the deferred load
    as a second SELECT.

    Deliberately asserted against a row that HAS an avatar. Against an account
    with none, a query that selected the bytes would come back with NULL and cost
    nothing measurable -- the test would pass on the defect.
    """

    async def test_should_not_name_avatar_bytes_in_any_statement_it_emits(self):
        engine = generation_test_engine()
        session_factory = create_session_factory(engine)
        account = Account.create(
            id=uuid4(),
            email=f"profile-sql-{uuid4()}@example.com",
            password_hash="hash",
            created_at=datetime.now(UTC),
        )

        captured: list[str] = []

        def record(conn, cursor, statement, parameters, context, executemany):  # noqa: ARG001 -- SQLAlchemy before_cursor_execute hook shape
            captured.append(" ".join(statement.split()).upper())

        try:
            async with session_factory() as setup:
                await SqlAlchemyAccountRepository(setup).save(account)
                await SqlAlchemyAvatarRepository(setup).update_avatar(
                    account_id=account.id,
                    data=b"\x89PNG\r\n\x1a\n" + b"\x00" * 4096,
                    media_type="image/png",
                    updated_at=datetime.now(UTC),
                )
                await setup.commit()

            async with session_factory() as session:
                event.listen(engine.sync_engine, "before_cursor_execute", record)
                try:
                    # Exactly what GetProfile calls. Reading the returned entity's
                    # avatar_updated_at is part of the profile response, so it is
                    # read here too -- if THAT triggered a deferred load, this test
                    # would see the extra statement.
                    profile = await SqlAlchemyAccountRepository(session).find_by_id(account.id)
                    assert profile is not None, "the seeded account must be readable"
                    assert profile.avatar_updated_at is not None, (
                        "the profile must report the avatar's update instant"
                    )
                finally:
                    event.remove(engine.sync_engine, "before_cursor_execute", record)

            offenders = [sql for sql in captured if AVATAR_BYTES_COLUMN in sql]
            assert offenders == [], (
                "the profile read must never name avatar_bytes. GET /me runs on every "
                "authenticated page view, so this puts the whole image on the product's "
                f"highest-rate query. Offending statements: {offenders}"
            )
        finally:
            await truncate(engine)
            await engine.dispose()
