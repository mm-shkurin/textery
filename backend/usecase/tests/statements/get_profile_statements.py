from auth.get_profile import GetProfile
from statements.profile_base import ProfileStatementsBase


class GetProfileStatements(ProfileStatementsBase):
    """`GET /api/v1/auth/me`: the caller's own profile, or 401."""

    async def read_the_profile(self) -> None:
        self.returned_account = await self._capture(
            GetProfile(account_repository=self.account_repository).execute(self.account_id)
        )

    def assert_the_profile_is_the_arranged_account(self) -> None:
        assert self.profile is self.arranged_account, (
            f"expected the account the repository holds, got a different object: {self.profile!r}"
        )

    def assert_the_profile_reports_the_email(self) -> None:
        assert self.profile.email == self.EMAIL

    def assert_the_profile_reports_the_name(self, expected: str | None) -> None:
        assert self.profile.name == expected, (
            f"expected the name {expected!r}, got {self.profile.name!r}"
        )

    def assert_the_profile_reports_no_avatar(self) -> None:
        assert self.profile.avatar_updated_at is None

    def assert_the_profile_reports_the_avatar_timestamp(self) -> None:
        assert self.profile.avatar_updated_at == self.FIXED_CLOCK_NOW

    def assert_the_read_asked_the_repository_for_the_callers_id_only(self) -> None:
        """No lookup by email, and no second query: the read is scoped by construction."""
        assert self.account_repository.find_by_email_call_count == 0, (
            "expected the profile read to resolve by id alone, but it looked an account up by email"
        )
