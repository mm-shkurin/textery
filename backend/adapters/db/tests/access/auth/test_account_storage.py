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

    async def test_should_raise_conflict_for_duplicate_email(
        self, account_storage_statements: AccountStorageStatements
    ):
        first = account_storage_statements.build_account(email="duplicate@example.com")
        await account_storage_statements.save_account(first)
        await account_storage_statements.save_account_with_duplicate_email("duplicate@example.com")
        account_storage_statements.assert_conflict_error_raised()


class TestSaveDoesNotCommitInternally:
    """Saving an account only flushes it onto the shared session — it stays
    pending until the shared UnitOfWork commits. A rollback issued on the
    session (as the UnitOfWork does on a later failure) discards it, so the
    account never lands durably without an explicit UnitOfWork.commit()."""

    async def test_should_not_persist_account_when_session_is_rolled_back_before_commit(
        self, account_storage_statements: AccountStorageStatements
    ):
        account = account_storage_statements.build_account(email="rollback@example.com")
        await account_storage_statements.save_account(account)
        await account_storage_statements.rollback_session()
        await account_storage_statements.assert_account_absent_on_new_connection()
