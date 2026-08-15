class TestDeletingWithAPassword:
    """An account that has a password can be confirmed by that password, and only by it."""

    async def test_should_erase_the_account_on_the_correct_password(
        self, delete_account_statements
    ):
        await delete_account_statements.given_an_account()
        await delete_account_statements.delete_with_the_correct_password()
        delete_account_statements.assert_the_account_was_erased_once()
        delete_account_statements.assert_the_work_was_committed_once()
        delete_account_statements.assert_no_rows_survived_the_removal()

    async def test_should_refuse_a_wrong_password_without_touching_anything(
        self, delete_account_statements
    ):
        await delete_account_statements.given_an_account()
        await delete_account_statements.delete_with_the_wrong_password()
        delete_account_statements.assert_refused_as_an_invalid_confirmation()
        delete_account_statements.assert_nothing_was_erased()
        delete_account_statements.assert_nothing_was_committed()

    async def test_should_refuse_a_request_carrying_no_confirmation_at_all(
        self, delete_account_statements
    ):
        await delete_account_statements.given_an_account()
        await delete_account_statements.delete_with_no_confirmation_at_all()
        delete_account_statements.assert_refused_as_an_invalid_confirmation()
        delete_account_statements.assert_nothing_was_erased()

    async def test_should_refuse_the_email_form_on_an_account_that_has_a_password(
        self, delete_account_statements
    ):
        # Accepting it would reduce the gate to knowing an address the deletion
        # screen is displaying.
        await delete_account_statements.given_an_account()
        await delete_account_statements.delete_with_the_email_while_the_account_has_a_password()
        delete_account_statements.assert_refused_as_an_invalid_confirmation()
        delete_account_statements.assert_nothing_was_erased()

    async def test_should_not_say_which_form_was_wrong(self, delete_account_statements):
        # One code for both causes: the caller already knows which form they sent.
        await delete_account_statements.given_an_account()
        await delete_account_statements.delete_with_the_wrong_password()
        delete_account_statements.assert_the_refusal_does_not_say_which_form_was_wrong()


class TestDeletingAnOAuthAccount:
    """No password could ever confirm it -- including "", which is what is stored."""

    async def test_should_erase_the_account_on_its_own_address(self, delete_account_statements):
        await delete_account_statements.given_an_oauth_account()
        await delete_account_statements.delete_with_the_accounts_own_email()
        delete_account_statements.assert_the_account_was_erased_once()
        delete_account_statements.assert_no_rows_survived_the_removal()

    async def test_should_refuse_someone_elses_address(self, delete_account_statements):
        await delete_account_statements.given_an_oauth_account()
        await delete_account_statements.delete_with_someone_elses_email()
        delete_account_statements.assert_refused_as_an_invalid_confirmation()
        delete_account_statements.assert_nothing_was_erased()

    async def test_should_refuse_an_empty_password_rather_than_match_the_stored_hash(
        self, delete_account_statements
    ):
        # The stored hash IS "". A comparison written as "does the submitted value
        # match the stored one" deletes this account for a body of {"password": ""}.
        await delete_account_statements.given_an_oauth_account()
        await delete_account_statements.delete_with_an_empty_password()
        delete_account_statements.assert_refused_as_an_invalid_confirmation()
        delete_account_statements.assert_nothing_was_erased()

    async def test_should_refuse_the_correct_password_form_on_an_account_with_no_password(
        self, delete_account_statements
    ):
        await delete_account_statements.given_an_oauth_account()
        await delete_account_statements.delete_with_the_correct_password()
        delete_account_statements.assert_refused_as_an_invalid_confirmation()


class TestDeletionFailures:
    async def test_should_refuse_a_token_whose_account_row_is_already_gone(
        self, delete_account_statements
    ):
        delete_account_statements.given_no_account_exists_for_the_token_subject()
        await delete_account_statements.delete_with_the_correct_password()
        delete_account_statements.assert_refused_as_unauthorized()
        delete_account_statements.assert_nothing_was_erased()

    async def test_should_take_back_the_child_deletions_when_the_removal_fails_halfway(
        self, delete_account_statements
    ):
        # The worst outcome available in this product: an account whose documents
        # are gone. Nothing downstream can catch it and nothing can undo it, so the
        # rollback is the only thing standing between the user and that state.
        await delete_account_statements.given_an_account()
        delete_account_statements.given_the_erase_fails_after_the_children_are_gone()
        await delete_account_statements.delete_with_the_correct_password()
        delete_account_statements.assert_the_failure_reached_the_caller()
        delete_account_statements.assert_the_work_was_rolled_back()
        delete_account_statements.assert_every_removed_row_came_back()

    async def test_should_take_everything_back_when_the_commit_fails(
        self, delete_account_statements
    ):
        await delete_account_statements.given_an_account()
        delete_account_statements.given_the_commit_fails()
        await delete_account_statements.delete_with_the_correct_password()
        delete_account_statements.assert_the_failure_reached_the_caller()
        delete_account_statements.assert_the_work_was_rolled_back()
        delete_account_statements.assert_every_removed_row_came_back()
