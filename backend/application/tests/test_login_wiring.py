from unittest.mock import AsyncMock, MagicMock, patch

from container.auth_wiring import create_login_user
from session import SqlAlchemyUnitOfWork


class TestCreateLoginUserSharesOneSession:
    """The failed-attempt increment (scenario 5.3) only survives if the wrong-password
    branch's ``unit_of_work.commit()`` actually commits. That holds only when
    ``create_login_user`` hands ``LoginUser`` a real ``SqlAlchemyUnitOfWork`` bound to
    the SAME session as the account repository -- so the increment and the commit run
    in ONE transaction.

    ``LoginUser.__init__`` defaults an unsupplied ``unit_of_work`` to ``NullUnitOfWork``,
    whose ``commit()`` is a silent no-op: the increment is issued on the session but
    never committed, then discarded on ``session.close()``. The counter stays 0 in
    production with ZERO visible symptom (the acceptance guard is ``[S]``). This pins the
    wiring directly -- session identity alone can't catch an unwired UoW because a
    ``NullUnitOfWork`` never touches a session, so the concrete type must be asserted.
    """

    async def test_should_wire_a_real_uow_sharing_the_repository_session(self):
        sentinel_session = MagicMock()
        sentinel_session.close = AsyncMock()

        with patch(
            "container.auth_wiring.session_factory", return_value=sentinel_session
        ):
            login_generator = create_login_user()
            login = await login_generator.__anext__()
            try:
                assert isinstance(login.unit_of_work, SqlAlchemyUnitOfWork), (
                    "expected create_login_user to wire a real SqlAlchemyUnitOfWork so "
                    "the failed-attempt commit is not a silent no-op, got "
                    f"{login.unit_of_work!r}"
                )

                account_session = login.account_repository._session
                unit_of_work_session = login.unit_of_work._session

                assert account_session is sentinel_session, (
                    "expected the account repository to be backed by the wiring's "
                    f"single session, got a different object {account_session!r}"
                )
                assert unit_of_work_session is sentinel_session, (
                    "expected the UnitOfWork to share the wiring's single session so the "
                    f"failed-attempt increment and its commit are one transaction, got "
                    f"{unit_of_work_session!r}"
                )
            finally:
                await login_generator.aclose()
