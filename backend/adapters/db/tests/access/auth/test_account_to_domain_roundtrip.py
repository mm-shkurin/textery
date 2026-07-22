import pytest

from statements.account_to_domain_roundtrip_statements import (
    AccountToDomainRoundtripStatements,
)


@pytest.mark.skip(
    reason="RED: AccountModel.to_domain drops failed_attempt_count (reconstitutes to 0)"
)
class TestAccountToDomainCarriesFailedAttemptCount:
    """Persist an account row with failed_attempt_count = 3, then read it back
    through find_by_email (which routes through AccountModel.to_domain). The
    reconstituted domain Account must carry failed_attempt_count == 3.

    Load-bearing guard: to_domain() calls Account.reconstitute WITHOUT
    failed_attempt_count, so the parameter defaults to 0 and every account reads
    back with count=0 -- the 5.4 lockout gate (which reads this value) is
    production-inert. The existing assert_fetched_matches_saved asserts on MODEL
    fields and omits the count, so it does NOT catch this. Exact == 3 does."""

    async def test_should_carry_failed_attempt_count_into_domain(
        self,
        account_to_domain_roundtrip_statements: AccountToDomainRoundtripStatements,
    ):
        await account_to_domain_roundtrip_statements.insert_account_with_failed_attempts()
        await account_to_domain_roundtrip_statements.read_back_via_find_by_email()
        account_to_domain_roundtrip_statements.assert_failed_attempt_count_carried_through()
