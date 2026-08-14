class TestWhichBranchAnAccountIsOn:
    """The branch is chosen by what the ACCOUNT has, never by what the client sent."""

    async def test_should_report_a_password_account_as_confirmable_by_password(
        self, deletion_confirmation_statements
    ):
        deletion_confirmation_statements.given_an_account_with_a_password()
        deletion_confirmation_statements.ask_whether_the_account_has_a_password()
        deletion_confirmation_statements.assert_confirmed()

    async def test_should_report_an_oauth_account_as_having_no_password(
        self, deletion_confirmation_statements
    ):
        # Its stored hash is "", which is what makes a naive "does the submitted
        # value match the stored one" comparison delete the account for an empty body.
        deletion_confirmation_statements.given_an_oauth_account()
        deletion_confirmation_statements.ask_whether_the_account_has_a_password()
        deletion_confirmation_statements.assert_not_confirmed()


class TestPasswordConfirmation:
    async def test_should_confirm_the_correct_password(self, deletion_confirmation_statements):
        deletion_confirmation_statements.given_an_account_with_a_password()
        deletion_confirmation_statements.confirm_with_the_correct_password()
        deletion_confirmation_statements.assert_confirmed()

    async def test_should_refuse_a_wrong_password(self, deletion_confirmation_statements):
        deletion_confirmation_statements.given_an_account_with_a_password()
        deletion_confirmation_statements.confirm_with_password("Wr0ng!Pass")
        deletion_confirmation_statements.assert_not_confirmed()

    async def test_should_refuse_an_empty_password_on_an_oauth_account_before_the_hasher(
        self, deletion_confirmation_statements
    ):
        # The single most destructive path in the product, and the reason the guard
        # is here rather than left to bcrypt's own handling of a "" hash.
        deletion_confirmation_statements.given_an_oauth_account()
        deletion_confirmation_statements.confirm_with_password("")
        deletion_confirmation_statements.assert_not_confirmed()
        deletion_confirmation_statements.assert_the_hasher_was_never_reached()

    async def test_should_refuse_any_password_on_an_account_that_has_none(
        self, deletion_confirmation_statements
    ):
        deletion_confirmation_statements.given_an_oauth_account()
        deletion_confirmation_statements.confirm_with_password("Str0ng!Pass")
        deletion_confirmation_statements.assert_not_confirmed()
        deletion_confirmation_statements.assert_the_hasher_was_never_reached()

    async def test_should_refuse_an_empty_password_on_an_account_that_has_one(
        self, deletion_confirmation_statements
    ):
        deletion_confirmation_statements.given_an_account_with_a_password()
        deletion_confirmation_statements.confirm_with_password("")
        deletion_confirmation_statements.assert_not_confirmed()
        deletion_confirmation_statements.assert_the_hasher_was_never_reached()

    async def test_should_refuse_a_password_field_that_is_not_a_string(
        self, deletion_confirmation_statements
    ):
        # The request DTO types the field permissively so the value arrives here
        # instead of triggering a 422 that echoes the rejected input back.
        deletion_confirmation_statements.given_an_account_with_a_password()
        deletion_confirmation_statements.confirm_with_password(None)
        deletion_confirmation_statements.assert_not_confirmed()
        deletion_confirmation_statements.assert_the_hasher_was_never_reached()

    async def test_should_refuse_a_password_field_holding_a_structure(
        self, deletion_confirmation_statements
    ):
        deletion_confirmation_statements.given_an_account_with_a_password()
        deletion_confirmation_statements.confirm_with_password({"password": "Str0ng!Pass"})
        deletion_confirmation_statements.assert_not_confirmed()

    async def test_should_confirm_a_decomposed_submission_of_a_precomposed_password(
        self, deletion_confirmation_statements
    ):
        # The hash was computed from the NFC form. Without normalizing here the
        # owner of the account cannot delete it from a keyboard that emits NFD.
        deletion_confirmation_statements.given_an_account_with_an_accented_password_stored_precomposed()
        deletion_confirmation_statements.confirm_with_the_decomposed_form_of_the_password()
        deletion_confirmation_statements.assert_confirmed()

    async def test_should_confirm_a_stored_password_that_no_longer_meets_the_policy(
        self, deletion_confirmation_statements
    ):
        # Deliberately not run through Password(...): a credential predating a
        # policy change must still be usable by its owner.
        deletion_confirmation_statements.given_an_account_with_a_password("weakpw")
        deletion_confirmation_statements.confirm_with_password("weakpw")
        deletion_confirmation_statements.assert_confirmed()


class TestEmailConfirmation:
    async def test_should_confirm_the_accounts_own_address_on_an_oauth_account(
        self, deletion_confirmation_statements
    ):
        deletion_confirmation_statements.given_an_oauth_account()
        deletion_confirmation_statements.confirm_with_the_accounts_own_email()
        deletion_confirmation_statements.assert_confirmed()

    async def test_should_refuse_an_address_on_an_account_that_has_a_password(
        self, deletion_confirmation_statements
    ):
        # Otherwise the gate reduces to knowing an email the user is looking at --
        # the deletion screen displays it.
        deletion_confirmation_statements.given_an_account_with_a_password()
        deletion_confirmation_statements.confirm_with_the_accounts_own_email()
        deletion_confirmation_statements.assert_not_confirmed()

    async def test_should_refuse_someone_elses_address(self, deletion_confirmation_statements):
        deletion_confirmation_statements.given_an_oauth_account()
        deletion_confirmation_statements.confirm_with_email("grace@example.ru")
        deletion_confirmation_statements.assert_not_confirmed()

    async def test_should_confirm_the_address_typed_in_a_different_case(
        self, deletion_confirmation_statements
    ):
        deletion_confirmation_statements.given_an_oauth_account()
        deletion_confirmation_statements.confirm_with_email("ADA@Example.RU")
        deletion_confirmation_statements.assert_confirmed()

    async def test_should_confirm_the_address_with_surrounding_whitespace(
        self, deletion_confirmation_statements
    ):
        deletion_confirmation_statements.given_an_oauth_account()
        deletion_confirmation_statements.confirm_with_email("  ada@example.ru  ")
        deletion_confirmation_statements.assert_confirmed()

    async def test_should_confirm_the_decomposed_form_of_an_accented_address(
        self, deletion_confirmation_statements
    ):
        # The address was stored NFC. A browser or keyboard that submits NFD sends
        # the same address and a different string; comparing raw would lock the
        # owner of an accented address out of deleting their own account.
        deletion_confirmation_statements.given_an_oauth_account_whose_address_carries_an_accent()
        deletion_confirmation_statements.confirm_with_the_decomposed_form_of_the_address()
        deletion_confirmation_statements.assert_confirmed()

    async def test_should_treat_a_syntactically_invalid_address_as_a_plain_mismatch(
        self, deletion_confirmation_statements
    ):
        # Not a separate INVALID_EMAIL: this endpoint has exactly one refusal.
        deletion_confirmation_statements.given_an_oauth_account()
        deletion_confirmation_statements.confirm_with_email("not-an-email")
        deletion_confirmation_statements.assert_not_confirmed()

    async def test_should_refuse_an_email_field_that_is_not_a_string(
        self, deletion_confirmation_statements
    ):
        deletion_confirmation_statements.given_an_oauth_account()
        deletion_confirmation_statements.confirm_with_email(None)
        deletion_confirmation_statements.assert_not_confirmed()

    async def test_should_refuse_an_email_field_holding_a_structure(
        self, deletion_confirmation_statements
    ):
        deletion_confirmation_statements.given_an_oauth_account()
        deletion_confirmation_statements.confirm_with_email(["ada@example.ru"])
        deletion_confirmation_statements.assert_not_confirmed()

    async def test_should_refuse_an_empty_address(self, deletion_confirmation_statements):
        deletion_confirmation_statements.given_an_oauth_account()
        deletion_confirmation_statements.confirm_with_email("")
        deletion_confirmation_statements.assert_not_confirmed()
