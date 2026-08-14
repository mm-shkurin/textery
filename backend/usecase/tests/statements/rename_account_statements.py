import unicodedata

from auth.rename_account import RenameAccount
from shared.exceptions import ValidationException
from statements.profile_base import ProfileStatementsBase


class RenameAccountStatements(ProfileStatementsBase):
    """`PATCH /api/v1/auth/me`: set or clear the display name."""

    NEW_NAME = "Grace Hopper"
    NAME_NEEDING_NORMALIZATION = "  " + unicodedata.normalize("NFD", "Renée") + "  "
    NORMALIZED_NAME = unicodedata.normalize("NFC", "Renée")
    INVALID_NAME_CODE = "INVALID_NAME"

    def __init__(self) -> None:
        super().__init__()
        self.write_failure = RuntimeError("the UPDATE failed")

    async def rename_to(self, name: object) -> None:
        self.returned_account = await self._capture(self._usecase().execute(self.account_id, name))

    async def rename_to_a_name_needing_normalization(self) -> None:
        await self.rename_to(self.NAME_NEEDING_NORMALIZATION)

    async def clear_the_name(self) -> None:
        await self.rename_to(None)

    def given_the_update_fails(self) -> None:
        self.account_repository.raise_on_update_name = self.write_failure

    def given_the_commit_fails(self) -> None:
        self.unit_of_work.raise_on_commit = self.write_failure

    def _usecase(self) -> RenameAccount:
        return RenameAccount(
            account_repository=self.account_repository, unit_of_work=self.unit_of_work
        )

    def assert_the_stored_name_is(self, expected: str | None) -> None:
        assert self.account_repository.update_name_calls == [(self.account_id, expected)], (
            f"expected one single-column UPDATE writing {expected!r}, got "
            f"{self.account_repository.update_name_calls!r}"
        )

    def assert_the_returned_profile_reports(self, expected: str | None) -> None:
        assert self.profile.name == expected, (
            f"expected the response to carry {expected!r}, got {self.profile.name!r}"
        )

    def assert_the_account_was_never_read(self) -> None:
        """A malformed name costs zero queries, so it cannot be timed against a
        well-formed one on a missing account."""
        assert self.account_repository.update_name_calls == []

    def assert_refused_as_an_invalid_name(self) -> None:
        assert isinstance(self.thrown_exception, ValidationException), (
            f"expected a ValidationException, got {self.thrown_exception!r}"
        )
        assert self.thrown_exception.error_code == self.INVALID_NAME_CODE

    def assert_the_write_failure_reached_the_caller(self) -> None:
        assert self.thrown_exception is self.write_failure, (
            "expected the original failure to propagate rather than be swallowed, got "
            f"{self.thrown_exception!r}"
        )

    def assert_the_work_was_rolled_back(self) -> None:
        assert self.unit_of_work.rollback_call_count == 1, (
            f"expected exactly one rollback, got {self.unit_of_work.rollback_call_count}"
        )

    def assert_the_entity_still_carries_its_old_name(self, expected: str | None) -> None:
        assert self.arranged_account.name == expected, (
            "expected the in-memory entity to be left untouched by a failed write, got "
            f"{self.arranged_account.name!r}"
        )
