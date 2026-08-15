from tests.backend.abstract_backend_test import AbstractBackendTest


class TestClearingTheName(AbstractBackendTest):
    """PATCH with an empty string removes the display name and answers 200.

    The clearing branch is the one an `if name:` guard silently breaks: the value
    that clears IS falsy, so a truthiness-guarded assignment answers 200, reports
    the name as gone, and leaves the old one in the row. The re-read is a second
    HTTP request and therefore a different server-side session, which is what
    makes it evidence about the database rather than about an identity map."""

    async def test_should_clear_the_name_and_report_null_on_a_later_read(
        self, profile_statements
    ):
        cleared, reread = await profile_statements.set_name_then_clear_it()

        profile_statements.assert_the_name_was_cleared(cleared, reread)


class TestSixtyCodePointName(AbstractBackendTest):
    """A 60-emoji name is accepted and comes back byte for byte.

    60 code points, 120 UTF-16 units, 240 UTF-8 bytes. The bound is 60 CODE
    POINTS, so only that reading accepts this name — a limit implemented in bytes
    or in UTF-16 units refuses it, and a VARCHAR(60) column would refuse it from
    the driver as a 500."""

    async def test_should_store_and_return_a_sixty_code_point_name_unchanged(
        self, profile_statements
    ):
        stored, reread = await profile_statements.store_a_sixty_emoji_name()

        profile_statements.assert_the_emoji_name_round_tripped(stored, reread)


class TestTheProfileNamesItsDeletionConfirmationForm(AbstractBackendTest):
    """The profile reports whether this account can be confirmed by password.

    The deletion route accepts a password ONLY from an account that has one, and
    an address ONLY from one that does not. Nothing else on the wire lets a client
    tell the two apart — the hash is not there and must not be. Without this key
    the client falls back to the address form for everyone, the backend refuses
    every password account on it, and there is no second form to fall back to:
    deletion becomes impossible for them. That is exactly what shipped, and this
    is the assertion that would have caught it."""

    async def test_should_report_has_password_for_a_password_account(self, profile_statements):
        profile = await profile_statements.read_the_profile_of_a_password_account()

        profile_statements.assert_the_profile_names_its_confirmation_form(profile)


class TestBothRoutesRefuseInvalidCredentials(AbstractBackendTest):
    """Neither route serves anything without a valid access token.

    Four calls — GET and PATCH, each with no header and with a forged token — and
    one identical refusal. Asserted together because the claim is about their
    SAMENESS: a per-route or per-cause difference is an oracle telling the caller
    which half of the header they got right."""

    async def test_should_answer_401_identically_on_both_routes(self, profile_statements):
        responses = await profile_statements.call_both_routes_without_a_valid_token()

        profile_statements.assert_every_call_was_refused_identically(responses)


class TestNulNameIsRefusedNotCrashed(AbstractBackendTest):
    """A name of one NUL answers 400 INVALID_NAME, never 500.

    U+0000 is under both length bounds and passes every "does it have visible
    characters" filter, so a predicate borrowed from the topic rules lets it
    through — and Postgres's `text` type then refuses it from the driver, turning
    a documented 400 into an internal server error. This is the one test of the
    canonical error envelope on this route."""

    async def test_should_refuse_a_nul_name_in_the_canonical_error_envelope(
        self, profile_statements
    ):
        response = await profile_statements.submit_a_name_of_one_nul()

        profile_statements.assert_the_nul_name_was_refused_in_the_canonical_envelope(response)
