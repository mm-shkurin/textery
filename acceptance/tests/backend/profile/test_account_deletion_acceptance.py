from tests.backend.abstract_backend_test import AbstractBackendTest


class TestDeletionEndsEverySessionImmediately(AbstractBackendTest):
    """After the account is deleted, its still-unexpired access token is refused.

    Nothing revokes the token and nothing needs to: it stays cryptographically
    valid for up to fifteen minutes, but `get_current_owner_id` confirms the
    account row exists on every authenticated request, so the next call from any
    tab or device answers 401 — indistinguishable from a forged token. This is the
    test that keeps that property from being optimised away: the day someone drops
    the existence check to save a query, a deleted user's tabs keep working for a
    quarter of an hour."""

    async def test_should_refuse_the_old_access_token_on_the_profile(self, deletion_statements):
        outcome = await deletion_statements.delete_a_password_account_then_reuse_its_token()

        deletion_statements.assert_the_session_is_dead_immediately(outcome)


class TestAPasswordAccountCannotBeDeletedByItsEmail(AbstractBackendTest):
    """An account that HAS a password is not deletable by retyping its address.

    The branch is chosen by the account, never by the request. The deletion screen
    shows the user their own email, so accepting `confirm_email` on an account
    with a password would reduce the password gate to reading the page — anyone
    with a borrowed session could destroy the account without knowing the
    credential."""

    async def test_should_refuse_confirm_email_when_the_account_has_a_password(
        self, deletion_statements
    ):
        response = await deletion_statements.confirm_a_password_account_with_its_own_email()

        deletion_statements.assert_refused(
            response, "an address submitted for an account that has a password"
        )


class TestAnOAuthAccountIsConfirmedByItsAddressOnly(AbstractBackendTest):
    """An account with no password: only its own address deletes it.

    OAuth accounts are stored with `password_hash == ""`. `{"password": ""}` is
    the shape that makes a naive check — "does the submitted value match the
    stored one" — delete the account for an empty body, so it is asserted here
    against the real hasher over real HTTP rather than against a stub that could
    define the problem away. Someone else's address is refused too, which is what
    makes the accepted case a confirmation rather than a formality."""

    async def test_should_refuse_an_empty_password_and_a_foreign_address_but_accept_its_own(
        self, deletion_statements
    ):
        attempts = await deletion_statements.try_every_confirmation_on_an_oauth_account()

        deletion_statements.assert_only_the_own_email_deleted(attempts)
