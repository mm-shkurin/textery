from auth.delete_account import DeleteAccount
from fake.auth.fake_account_eraser import FakeAccountEraser
from shared.exceptions import ValidationException
from statements.profile_base import ProfileStatementsBase


class DeleteAccountStatements(ProfileStatementsBase):
    """`DELETE /api/v1/auth/me`: the only irreversible operation in the product."""

    CONFIRMATION_INVALID_CODE = "DELETION_CONFIRMATION_INVALID"
    WRONG_PASSWORD = "Wr0ng!Pass"
    SOMEONE_ELSES_EMAIL = "grace@example.ru"

    def __init__(self) -> None:
        super().__init__()
        self._account_eraser = FakeAccountEraser()
        self.erase_failure = RuntimeError("the account row could not be deleted")
        self._unit_of_work.rollback_hooks.append(self._undo_the_erase)

    def given_the_erase_fails_after_the_children_are_gone(self) -> None:
        """The one half-done state the real eraser can reach.

        Its five DELETEs run children-first, so a failure on the LAST one leaves a
        transaction in which the documents are gone and the account is not.
        """
        self._account_eraser.erase_after_children_removed = self.erase_failure

    def given_the_commit_fails(self) -> None:
        self._unit_of_work.raise_on_commit = self.erase_failure

    async def delete_with_the_correct_password(self) -> None:
        await self._delete(password=self.PASSWORD)

    async def delete_with_the_wrong_password(self) -> None:
        await self._delete(password=self.WRONG_PASSWORD)

    async def delete_with_an_empty_password(self) -> None:
        await self._delete(password="")

    async def delete_with_no_confirmation_at_all(self) -> None:
        await self._delete()

    async def delete_with_the_accounts_own_email(self) -> None:
        await self._delete(confirm_email=self.EMAIL)

    async def delete_with_someone_elses_email(self) -> None:
        await self._delete(confirm_email=self.SOMEONE_ELSES_EMAIL)

    async def delete_with_the_email_while_the_account_has_a_password(self) -> None:
        await self._delete(confirm_email=self.EMAIL)

    async def _delete(self, password: object = None, confirm_email: object = None) -> None:
        await self._capture(
            DeleteAccount(
                account_repository=self._account_repository,
                account_eraser=self._account_eraser,
                password_hasher=self._password_hasher,
                unit_of_work=self._unit_of_work,
            ).execute(self.account_id, password=password, confirm_email=confirm_email)
        )

    def _undo_the_erase(self) -> None:
        self._account_eraser.removed_rows.clear()

    def assert_the_account_was_erased_once(self) -> None:
        assert self._account_eraser.erase_calls == [self.account_id], (
            f"expected one erase for the caller's own id, got {self._account_eraser.erase_calls!r}"
        )

    def assert_nothing_was_erased(self) -> None:
        assert self._account_eraser.erase_calls == [], (
            "expected a refused confirmation to never reach the eraser, got "
            f"{self._account_eraser.erase_calls!r}"
        )

    def assert_no_rows_survived_the_removal(self) -> None:
        assert self._account_eraser.removed_rows == [
            *self._account_eraser.child_rows,
            "accounts",
        ], f"expected every row to be removed, got {self._account_eraser.removed_rows!r}"

    def assert_every_removed_row_came_back(self) -> None:
        """The whole point of the single transaction.

        Anything short of this leaves the caller holding an account whose
        documents are gone -- the one outcome in this product that cannot be
        undone and that nothing downstream reports.
        """
        assert self._account_eraser.removed_rows == [], (
            "expected the rollback to take the child deletions back too, but these "
            f"rows stayed removed: {self._account_eraser.removed_rows!r}"
        )

    def assert_the_failure_reached_the_caller(self) -> None:
        assert self.thrown_exception is self.erase_failure, (
            "expected the original failure to propagate so the client is never told "
            f"the account is gone, got {self.thrown_exception!r}"
        )

    def assert_the_work_was_rolled_back(self) -> None:
        assert self._unit_of_work.rollback_call_count == 1, (
            f"expected exactly one rollback, got {self._unit_of_work.rollback_call_count}"
        )

    def assert_refused_as_an_invalid_confirmation(self) -> None:
        assert isinstance(self.thrown_exception, ValidationException), (
            f"expected a ValidationException, got {self.thrown_exception!r}"
        )
        assert self.thrown_exception.error_code == self.CONFIRMATION_INVALID_CODE

    def assert_the_refusal_does_not_say_which_form_was_wrong(self) -> None:
        # Same isinstance gate as the assertion above: without it, a refusal that
        # never happened reads as `None has no attribute message` instead of
        # "nothing was raised".
        assert isinstance(self.thrown_exception, ValidationException), (
            f"expected a ValidationException, got {self.thrown_exception!r}"
        )
        assert self.thrown_exception.message == (
            "The confirmation does not match. Nothing was deleted."
        )
