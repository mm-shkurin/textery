from unittest.mock import AsyncMock, MagicMock, patch

from container.auth_wiring import create_resend_code


class TestCreateResendCodeSharesOneSession:
    """The concurrent-resend guard (scenario 4.4) is a SELECT ... FOR UPDATE row
    lock that only serializes if the lock, the cooldown read, and the insert+commit
    all run in ONE database transaction. That holds only because
    ``create_resend_code`` builds the account repository, the verification-code
    repository, and the UnitOfWork from a single ``session_factory()`` session.

    That coupling is load-bearing and otherwise untested: the db-adapter race test
    hand-orchestrates the lock, and the usecase test no-ops it via a Fake, so
    neither drives the real wiring. This pins it directly -- it is green today and
    goes RED the moment a future refactor gives any collaborator its own session,
    silently un-serializing resend back to the double-issue bug.
    """

    async def test_should_back_all_collaborators_with_the_same_session(self):
        sentinel_session = MagicMock()
        sentinel_session.close = AsyncMock()

        with patch("container.auth_wiring.session_factory", return_value=sentinel_session):
            resend_generator = create_resend_code()
            resend = await resend_generator.__anext__()
            try:
                account_session = resend.account_repository._session
                code_session = resend.verification_code_repository._session
                unit_of_work_session = resend.unit_of_work._session

                assert account_session is sentinel_session, (
                    "expected the account repository to be backed by the wiring's "
                    f"single session, got a different object {account_session!r}"
                )
                assert code_session is sentinel_session, (
                    "expected the verification-code repository to share the wiring's "
                    f"single session, got a different object {code_session!r}"
                )
                assert unit_of_work_session is sentinel_session, (
                    "expected the UnitOfWork to share the wiring's single session so "
                    f"the FOR UPDATE lock and the commit are one transaction, got "
                    f"{unit_of_work_session!r}"
                )
            finally:
                await resend_generator.aclose()
