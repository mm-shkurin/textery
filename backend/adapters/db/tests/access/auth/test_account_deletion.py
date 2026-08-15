from statements.account_deletion_statements import AccountDeletionStatements


class TestDeletionRemovesEverythingThatBelongsToTheAccount:
    """A confirmed deletion leaves no row of that account in any of the five tables.

    Against a real Postgres, and it cannot be otherwise. Three of the child tables
    reference `accounts.id` with NO ACTION, so a wrong delete ORDER raises
    IntegrityError here and passes on fakes. `generations` is the only table with
    ON DELETE CASCADE, so its emptiness is a claim about the database and not
    about our code. And `documents.owner_id` has no foreign key at all — nothing
    cascades, nothing complains, and the user's text simply stays behind forever
    unless the explicit delete runs.

    This is the only irreversible operation in the product; there is no soft
    delete to fall back on and no way to check afterwards."""

    async def test_should_leave_no_row_of_the_deleted_account_anywhere(
        self, account_deletion_statements: AccountDeletionStatements
    ):
        statements = account_deletion_statements
        await statements.given_two_full_accounts()
        await statements.delete_the_owner_with_a_valid_confirmation()
        await statements.count_every_table_for_both_accounts()
        statements.assert_the_owner_is_gone_from_every_table()


class TestDeletionTouchesNoOtherAccount:
    """A second account with identical children keeps every one of its rows.

    The positive control for the claim above: `assert everything is gone` is also
    satisfied by a DELETE with a missing or mistyped owner predicate, which empties
    the table for every user at once. Only a bystander can tell those apart."""

    async def test_should_leave_the_other_accounts_rows_intact(
        self, account_deletion_statements: AccountDeletionStatements
    ):
        statements = account_deletion_statements
        await statements.given_two_full_accounts()
        await statements.delete_the_owner_with_a_valid_confirmation()
        await statements.count_every_table_for_both_accounts()
        statements.assert_the_bystander_is_untouched()


class TestARefusedConfirmationDeletesNothing:
    """A wrong password answers DELETION_CONFIRMATION_INVALID and removes no row.

    Asserted against the database rather than against a spy, because the failure
    worth ruling out is a deletion that runs and is then expected to be undone —
    a rollback that has to work, on the one operation where nothing can be
    recovered if it does not. Here the refusal happens before any statement is
    issued, and the row counts prove it."""

    async def test_should_keep_every_row_of_both_accounts(
        self, account_deletion_statements: AccountDeletionStatements
    ):
        statements = account_deletion_statements
        await statements.given_two_full_accounts()
        await statements.try_to_delete_the_owner_with_a_wrong_password()
        await statements.count_every_table_for_both_accounts()
        statements.assert_the_refusal_left_everything_in_place()
