from statements.rename_account_statements import RenameAccountStatements


class TestRenameAccount:
    """`PATCH /api/v1/auth/me`: set the display name."""

    async def test_should_store_the_new_name(self, rename_account_statements):
        await rename_account_statements.given_an_account()
        await rename_account_statements.rename_to(RenameAccountStatements.NEW_NAME)
        rename_account_statements.assert_the_stored_name_is(RenameAccountStatements.NEW_NAME)
        rename_account_statements.assert_the_work_was_committed_once()

    async def test_should_answer_with_the_whole_profile_carrying_the_new_name(
        self, rename_account_statements
    ):
        # The entity was read BEFORE the UPDATE, so it still carries the old name.
        # Applying the change to it is what makes the response the state the client
        # should now hold.
        await rename_account_statements.given_an_account(name="Ada Lovelace")
        await rename_account_statements.rename_to(RenameAccountStatements.NEW_NAME)
        rename_account_statements.assert_the_returned_profile_reports(
            RenameAccountStatements.NEW_NAME
        )

    async def test_should_store_the_normalized_name_rather_than_what_was_sent(
        self, rename_account_statements
    ):
        # A client that recomputed its dirty flag against what it SENT would show
        # "unsaved" forever after saving a name with a trailing space.
        await rename_account_statements.given_an_account()
        await rename_account_statements.rename_to_a_name_needing_normalization()
        rename_account_statements.assert_the_stored_name_is(RenameAccountStatements.NORMALIZED_NAME)
        rename_account_statements.assert_the_returned_profile_reports(
            RenameAccountStatements.NORMALIZED_NAME
        )


class TestClearingTheName:
    """Clearing is a rename to nothing, answered with 200 -- not a 400 and not a DELETE."""

    async def test_should_clear_a_name_on_an_explicit_null(self, rename_account_statements):
        await rename_account_statements.given_an_account(name="Ada Lovelace")
        await rename_account_statements.clear_the_name()
        rename_account_statements.assert_the_stored_name_is(None)
        rename_account_statements.assert_the_returned_profile_reports(None)

    async def test_should_clear_a_name_on_a_value_that_renders_as_nothing(
        self, rename_account_statements
    ):
        await rename_account_statements.given_an_account(name="Ada Lovelace")
        await rename_account_statements.rename_to("   ")
        rename_account_statements.assert_the_stored_name_is(None)

    async def test_should_write_the_column_even_when_the_new_value_is_nothing(
        self, rename_account_statements
    ):
        # There is no `if normalized:` guard in the usecase, and this is why: the
        # cleared value IS None, so skipping the write would make "clear my name" a
        # 200 that changed nothing.
        await rename_account_statements.given_an_account(name="Ada Lovelace")
        await rename_account_statements.clear_the_name()
        rename_account_statements.assert_the_work_was_committed_once()


class TestRenameRefusals:
    async def test_should_refuse_an_invalid_name_without_reading_the_account(
        self, rename_account_statements
    ):
        # Validation runs first, so a malformed name costs zero queries and cannot
        # be told apart by timing from a well-formed one against a missing account.
        await rename_account_statements.given_an_account()
        await rename_account_statements.rename_to("a" * 61)
        rename_account_statements.assert_refused_as_an_invalid_name()
        rename_account_statements.assert_the_account_was_never_read()
        rename_account_statements.assert_nothing_was_committed()

    async def test_should_refuse_a_name_that_is_not_a_string(self, rename_account_statements):
        await rename_account_statements.given_an_account()
        await rename_account_statements.rename_to(123)
        rename_account_statements.assert_refused_as_an_invalid_name()

    async def test_should_refuse_a_token_whose_account_row_is_gone(self, rename_account_statements):
        rename_account_statements.given_no_account_exists_for_the_token_subject()
        await rename_account_statements.rename_to(RenameAccountStatements.NEW_NAME)
        rename_account_statements.assert_refused_as_unauthorized()
        rename_account_statements.assert_nothing_was_committed()


class TestRenameFailures:
    async def test_should_roll_back_and_propagate_when_the_update_fails(
        self, rename_account_statements
    ):
        await rename_account_statements.given_an_account(name="Ada Lovelace")
        rename_account_statements.given_the_update_fails()
        await rename_account_statements.rename_to(RenameAccountStatements.NEW_NAME)
        rename_account_statements.assert_the_write_failure_reached_the_caller()
        rename_account_statements.assert_the_work_was_rolled_back()
        rename_account_statements.assert_the_entity_still_carries_its_old_name("Ada Lovelace")

    async def test_should_roll_back_and_propagate_when_the_commit_fails(
        self, rename_account_statements
    ):
        # A swallowed commit failure is a 200 over an unchanged row -- the exact
        # silent outcome the real UnitOfWork wiring exists to prevent.
        await rename_account_statements.given_an_account()
        rename_account_statements.given_the_commit_fails()
        await rename_account_statements.rename_to(RenameAccountStatements.NEW_NAME)
        rename_account_statements.assert_the_write_failure_reached_the_caller()
        rename_account_statements.assert_the_work_was_rolled_back()
