from statements.get_profile_statements import GetProfileStatements


class TestGetProfile:
    """`GET /api/v1/auth/me`: the caller's own profile, resolved from the token."""

    async def test_should_return_the_account_the_token_subject_names(
        self, get_profile_statements: GetProfileStatements
    ):
        await get_profile_statements.given_an_account()
        await get_profile_statements.read_the_profile()
        get_profile_statements.assert_the_profile_is_the_arranged_account()
        get_profile_statements.assert_the_profile_reports_the_email()

    async def test_should_report_a_name_of_null_for_an_account_that_has_none(
        self, get_profile_statements: GetProfileStatements
    ):
        # None is a value the read emits, not an absence to paper over: the header
        # chooses its email fallback from exactly this.
        await get_profile_statements.given_an_account()
        await get_profile_statements.read_the_profile()
        get_profile_statements.assert_the_profile_reports_the_name(None)

    async def test_should_report_the_stored_display_name(
        self, get_profile_statements: GetProfileStatements
    ):
        await get_profile_statements.given_an_account(name=GetProfileStatements.NAME)
        await get_profile_statements.read_the_profile()
        get_profile_statements.assert_the_profile_reports_the_name(GetProfileStatements.NAME)

    async def test_should_report_no_avatar_for_an_account_that_has_none(
        self, get_profile_statements: GetProfileStatements
    ):
        await get_profile_statements.given_an_account()
        await get_profile_statements.read_the_profile()
        get_profile_statements.assert_the_profile_reports_no_avatar()

    async def test_should_report_when_the_avatar_last_changed(
        self, get_profile_statements: GetProfileStatements
    ):
        await get_profile_statements.given_an_account(
            avatar_updated_at=GetProfileStatements.FIXED_CLOCK_NOW
        )
        await get_profile_statements.read_the_profile()
        get_profile_statements.assert_the_profile_reports_the_avatar_timestamp()

    async def test_should_resolve_the_profile_by_id_and_never_by_email(
        self, get_profile_statements: GetProfileStatements
    ):
        await get_profile_statements.given_an_account()
        await get_profile_statements.read_the_profile()
        get_profile_statements.assert_the_read_asked_the_repository_for_the_callers_id_only()

    async def test_should_refuse_a_token_whose_account_row_is_gone(
        self, get_profile_statements: GetProfileStatements
    ):
        # 401, never 404. Distinguishing the two would tell the holder of a token
        # that it was well-formed, and nothing the client can do about either differs.
        get_profile_statements.given_no_account_exists_for_the_token_subject()
        await get_profile_statements.read_the_profile()
        get_profile_statements.assert_refused_as_unauthorized()
