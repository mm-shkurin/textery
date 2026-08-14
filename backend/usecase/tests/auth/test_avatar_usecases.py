from auth.avatar_format import PNG


class TestUpdateAvatar:
    """`PUT /api/v1/auth/me/avatar`: store the uploaded bytes, answer with the profile."""

    async def test_should_store_the_bytes_exactly_as_received(self, avatar_statements):
        # No decode, no re-encode, no metadata stripping: every one of those would
        # put an image decoder in the path of untrusted input.
        await avatar_statements.given_an_account()
        await avatar_statements.upload_a_png()
        avatar_statements.assert_the_stored_bytes_are_exactly_what_was_uploaded()

    async def test_should_store_the_type_read_from_the_magic_bytes(self, avatar_statements):
        await avatar_statements.given_an_account()
        await avatar_statements.upload_a_png()
        avatar_statements.assert_the_stored_media_type_is(PNG)

    async def test_should_store_jpeg_as_jpeg(self, avatar_statements):
        await avatar_statements.given_an_account()
        await avatar_statements.upload_a_jpeg()
        avatar_statements.assert_the_stored_media_type_is_jpeg()

    async def test_should_answer_with_the_instant_the_upload_was_stamped_with(
        self, avatar_statements
    ):
        await avatar_statements.given_an_account()
        await avatar_statements.upload_a_png()
        avatar_statements.assert_the_returned_profile_reports_the_upload_instant()
        avatar_statements.assert_the_stored_timestamp_matches_the_returned_one()

    async def test_should_commit_the_upload(self, avatar_statements):
        await avatar_statements.given_an_account()
        await avatar_statements.upload_a_png()
        avatar_statements.assert_the_work_was_committed_once()

    async def test_should_replace_an_avatar_that_is_already_there(self, avatar_statements):
        await avatar_statements.given_an_account()
        await avatar_statements.given_a_stored_avatar()
        await avatar_statements.upload_a_jpeg()
        avatar_statements.assert_the_stored_bytes_are_exactly_what_was_uploaded()
        avatar_statements.assert_the_stored_media_type_is_jpeg()


class TestUpdateAvatarRefusals:
    async def test_should_refuse_an_svg_before_anything_is_read_or_written(self, avatar_statements):
        # An SVG is a document that can carry <script>; serving one from this
        # origin is stored XSS against the whole application.
        await avatar_statements.given_an_account()
        await avatar_statements.upload_an_svg()
        avatar_statements.assert_refused_as_an_unsupported_type()
        avatar_statements.assert_nothing_reached_storage()
        avatar_statements.assert_nothing_was_committed()

    async def test_should_refuse_an_empty_body(self, avatar_statements):
        await avatar_statements.given_an_account()
        await avatar_statements.upload_an_empty_body()
        avatar_statements.assert_refused_as_an_unsupported_type()
        avatar_statements.assert_nothing_reached_storage()

    async def test_should_refuse_a_token_whose_account_row_is_gone(self, avatar_statements):
        avatar_statements.given_no_account_exists_for_the_token_subject()
        await avatar_statements.upload_a_png()
        avatar_statements.assert_refused_as_unauthorized()
        avatar_statements.assert_nothing_reached_storage()

    async def test_should_roll_back_and_propagate_when_the_write_fails(self, avatar_statements):
        await avatar_statements.given_an_account()
        avatar_statements.given_the_avatar_write_fails()
        await avatar_statements.upload_a_png()
        avatar_statements.assert_the_write_failure_reached_the_caller()
        avatar_statements.assert_the_work_was_rolled_back()
        avatar_statements.assert_no_avatar_is_stored()


class TestDeleteAvatar:
    """Idempotent by contract: the client's goal is "the account has no avatar"."""

    async def test_should_remove_a_stored_avatar(self, avatar_statements):
        await avatar_statements.given_an_account()
        await avatar_statements.given_a_stored_avatar()
        await avatar_statements.remove_the_avatar()
        avatar_statements.assert_no_avatar_is_stored()
        avatar_statements.assert_the_work_was_committed_once()

    async def test_should_answer_with_a_profile_reporting_no_avatar(self, avatar_statements):
        await avatar_statements.given_an_account()
        await avatar_statements.given_a_stored_avatar()
        await avatar_statements.remove_the_avatar()
        avatar_statements.assert_the_returned_profile_reports_no_avatar()

    async def test_should_succeed_on_an_account_that_has_no_avatar(self, avatar_statements):
        # A 404 here would make a retry after a dropped response look like a bug to
        # a client that did exactly the right thing.
        await avatar_statements.given_an_account()
        await avatar_statements.remove_the_avatar()
        avatar_statements.assert_the_avatar_was_cleared_once()
        avatar_statements.assert_the_returned_profile_reports_no_avatar()

    async def test_should_refuse_a_token_whose_account_row_is_gone(self, avatar_statements):
        avatar_statements.given_no_account_exists_for_the_token_subject()
        await avatar_statements.remove_the_avatar()
        avatar_statements.assert_refused_as_unauthorized()

    async def test_should_roll_back_and_propagate_when_the_clear_fails(self, avatar_statements):
        await avatar_statements.given_an_account()
        await avatar_statements.given_a_stored_avatar()
        avatar_statements.given_the_avatar_clear_fails()
        await avatar_statements.remove_the_avatar()
        avatar_statements.assert_the_write_failure_reached_the_caller()
        avatar_statements.assert_the_work_was_rolled_back()


class TestGetAvatar:
    async def test_should_serve_the_stored_bytes_under_the_stored_type(self, avatar_statements):
        await avatar_statements.given_an_account()
        await avatar_statements.given_a_stored_avatar()
        await avatar_statements.serve_the_avatar()
        avatar_statements.assert_the_served_bytes_and_type_are_the_stored_ones()

    async def test_should_answer_not_found_when_there_is_no_avatar(self, avatar_statements):
        # Never a 200 with an empty body: to a client that is indistinguishable
        # from a broken image.
        await avatar_statements.given_an_account()
        await avatar_statements.serve_the_avatar()
        avatar_statements.assert_refused_as_not_found()

    async def test_should_serve_an_uploaded_avatar_back_unchanged(self, avatar_statements):
        await avatar_statements.given_an_account()
        await avatar_statements.upload_a_jpeg()
        await avatar_statements.serve_the_avatar()
        avatar_statements.assert_the_served_bytes_and_type_are_the_stored_ones()
