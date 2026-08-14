from statements.avatar_storage_statements import AvatarStorageStatements


class TestAvatarIsPersisted:
    """Uploaded bytes are durable: written through the avatar repository, they
    come back identical on a DIFFERENT session, with the media type they were
    stored under and a non-NULL update instant.

    Against a real Postgres, never a fake. `avatar_bytes` is `bytea` and mapped
    `deferred`, and the columns are written by a statement that names them by
    hand -- a column dropped from that list writes nothing, raises nothing, and a
    list-backed fake holding the value in memory cannot reproduce it. The new
    session matters for the same reason it does for the display name:
    expire_on_commit=False means a same-session re-read is served from the
    identity map and stays green against a row that does not exist."""

    async def test_should_read_the_uploaded_avatar_back_on_a_new_session(
        self, avatar_storage_statements: AvatarStorageStatements
    ):
        statements = avatar_storage_statements
        await statements.given_a_verified_named_account_with_failed_attempts()
        await statements.upload_an_avatar()
        await statements.read_the_avatar_back_on_a_new_session()
        statements.assert_the_avatar_survived_the_round_trip()


class TestUploadTouchesNothingElse:
    """Uploading an avatar changes only the avatar columns.

    The account is verified, named, and carries failed_attempt_count > 0 before
    the upload, because those are the fields a careless write destroys: an upload
    routed through save() rewrites email and is_verified from a snapshot read
    earlier in the request, and an UPDATE naming more columns than it means to can
    wipe the display name or reset a lockout counter."""

    async def test_should_leave_name_email_verification_lockout_and_created_at_untouched(
        self, avatar_storage_statements: AvatarStorageStatements
    ):
        statements = avatar_storage_statements
        await statements.given_a_verified_named_account_with_failed_attempts()
        await statements.upload_an_avatar()
        await statements.read_the_whole_row_back_on_a_new_session()
        statements.assert_nothing_but_the_avatar_changed()
