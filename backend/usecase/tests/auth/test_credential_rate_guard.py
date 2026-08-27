import pytest

from statements.credential_rate_guard_statements import CredentialRateGuardStatements


@pytest.mark.skip(reason="RED: CredentialRateGuard.check is not implemented yet")
class TestCredentialRateGuard:
    """The per-source bound the password routes need on top of the account lockout.

    The lockout counts failures against ONE account, so a source that spreads its
    attempts across many accounts never trips it. These pin the bound that does
    count the source.
    """

    async def test_should_refuse_the_attempt_after_the_allowance_is_spent(
        self, credential_rate_guard_statements: CredentialRateGuardStatements
    ):
        await credential_rate_guard_statements.given_the_allowance_spent_by_one_source()
        await credential_rate_guard_statements.attempt_once_more()
        credential_rate_guard_statements.assert_refused_as_rate_limited()

    async def test_should_not_spend_another_sources_allowance(
        self, credential_rate_guard_statements: CredentialRateGuardStatements
    ):
        await credential_rate_guard_statements.given_the_allowance_spent_by_one_source()
        await credential_rate_guard_statements.attempt_from_another_source()
        credential_rate_guard_statements.assert_allowed()

    async def test_should_not_spend_another_routes_allowance(
        self, credential_rate_guard_statements: CredentialRateGuardStatements
    ):
        await credential_rate_guard_statements.given_the_allowance_spent_by_one_source()
        await credential_rate_guard_statements.attempt_on_another_route()
        credential_rate_guard_statements.assert_allowed()
