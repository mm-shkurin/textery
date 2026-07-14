from statements.account_storage_statements import AccountStorageStatements


class TestSave:
    """Saving an account persists id, email, password_hash, is_verified=False,
    and created_at exactly as passed in, ignoring any server-owned fields."""

    async def test_should_round_trip_saved_account(
        self, account_storage_statements: AccountStorageStatements
    ):
        account = account_storage_statements.build_account()
        await account_storage_statements.save_account(account)
        await account_storage_statements.fetch_saved_account_row()
        account_storage_statements.assert_fetched_matches_saved()
