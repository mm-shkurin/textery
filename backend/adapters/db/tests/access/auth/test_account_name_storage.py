from statements.account_name_storage_statements import AccountNameStorageStatements


class TestNameIsPersisted:
    """A saved display name is durable: written through the repository, it is
    still there when a DIFFERENT session reads the account back.

    Against a real Postgres, never a fake. Three hand-kept lists enumerate the
    account columns (save()'s update branch, from_domain, to_domain) and a field
    missing from one of them produces a write that flushes cleanly, answers 200,
    and stores nothing -- a list-backed fake holds the entity itself and cannot
    reproduce that. The new session is equally load-bearing: with
    expire_on_commit=False, a re-read on the writing session is served from the
    identity map and is green against a row that was never written."""

    async def test_should_read_the_saved_name_back_on_a_new_session(
        self, account_name_storage_statements: AccountNameStorageStatements
    ):
        statements = account_name_storage_statements
        await statements.given_a_verified_account_with_failed_attempts_and_a_name()
        await statements.read_the_account_back_on_a_new_session()
        statements.assert_the_name_survived_the_round_trip()


class TestRenameTouchesNothingElse:
    """Renaming an account changes the name and nothing else.

    The account is verified and carries failed_attempt_count > 0 before the
    rename, because those are the two fields a careless rename destroys: a rename
    routed through save() rewrites is_verified and email from an entity snapshot
    read before the change, and any UPDATE that names more columns than it means
    to can hand a locked-out attacker their attempts back."""

    async def test_should_leave_verification_lockout_email_and_created_at_untouched(
        self, account_name_storage_statements: AccountNameStorageStatements
    ):
        statements = account_name_storage_statements
        await statements.given_a_verified_account_with_failed_attempts_and_a_name()
        await statements.rename_the_account()
        await statements.read_the_whole_row_back_on_a_new_session()
        statements.assert_only_the_name_changed()
