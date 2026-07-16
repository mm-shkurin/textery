from statements.refresh_statements import RefreshStatements


class TestRefreshSuccess:
    """Scenario 6.2: a valid refresh token returns a fresh token pair."""

    async def test_should_issue_a_fresh_pair_for_a_valid_refresh_token(
        self, refresh_statements: RefreshStatements
    ):
        await refresh_statements.given_a_refresh_token_for_a_verified_account()
        await refresh_statements.submit_the_refresh_token()
        refresh_statements.assert_fresh_token_pair_issued_for_the_account()


class TestRefreshRejection:
    """Scenario 6.3: an expired, invalid or no-longer-usable token is rejected.

    Every case answers with the same error code and message, deliberately.
    """

    async def test_should_reject_a_token_the_token_service_will_not_read(
        self, refresh_statements: RefreshStatements
    ):
        await refresh_statements.given_a_token_the_token_service_rejects()
        await refresh_statements.submit_the_refresh_token()
        refresh_statements.assert_rejected_as_invalid_refresh_token()

    async def test_should_reject_a_token_naming_an_account_that_no_longer_exists(
        self, refresh_statements: RefreshStatements
    ):
        # The signature is still valid here -- only the account is gone. Trusting
        # the claims instead of re-reading the account would let a deleted user
        # keep minting access tokens for the token's remaining 7 days.
        await refresh_statements.given_a_refresh_token_for_an_account_that_no_longer_exists()
        await refresh_statements.submit_the_refresh_token()
        refresh_statements.assert_rejected_as_invalid_refresh_token()

    async def test_should_reject_a_token_for_an_account_that_is_no_longer_verified(
        self, refresh_statements: RefreshStatements
    ):
        # Same reason: the token outlives the state it was minted from, so
        # verification is re-checked at every refresh, not trusted from claims.
        await refresh_statements.given_a_refresh_token_for_an_account_that_since_became_unverified()
        await refresh_statements.submit_the_refresh_token()
        refresh_statements.assert_rejected_as_invalid_refresh_token()
