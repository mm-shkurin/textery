import pytest

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


class TestSaveDuplicateEmail:
    """Saving a second account with an email that already exists raises
    ConflictException instead of a raw database error or silent success,
    so RegisterUser.execute can translate it into EMAIL_ALREADY_REGISTERED."""

    @pytest.mark.skip(reason="RED: no unique constraint or ConflictException mapping in SqlAlchemyAccountRepository.save() yet")
    async def test_should_raise_conflict_for_duplicate_email(
        self, account_storage_statements: AccountStorageStatements
    ):
        first = account_storage_statements.build_account(email="duplicate@example.com")
        await account_storage_statements.save_account(first)
        await account_storage_statements.save_account_with_duplicate_email("duplicate@example.com")
        account_storage_statements.assert_conflict_error_raised()
