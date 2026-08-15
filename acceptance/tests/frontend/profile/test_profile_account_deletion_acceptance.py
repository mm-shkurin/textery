from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestProfileAccountDeletionAcceptance(AbstractFrontendTest):
    """UI: deleting the account, confirmed by password, and the exit that follows.

    Given a signed-in visitor on their profile screen
    When they open the danger zone and confirm with their password
    Then the account is deleted and they are left on the signed-out landing page
    """

    WRONG_PASSWORD = "Wr0ng!Pass"

    def test_should_delete_the_account_and_land_on_a_usable_page(
        self, webdriver, app_url, profile_page_statements, profile_deletion_statements
    ):
        # The 204 does not invalidate the access token -- these are stateless JWTs -- so an
        # identity request still in flight would resolve into an expired-session screen. The last
        # thing a user sees on the way out must not be an error about a session they ended.
        profile_page_statements.navigate_to_profile_page(webdriver, app_url)
        profile_deletion_statements.open_the_confirmation(webdriver)
        profile_deletion_statements.assert_the_password_form_is_shown(webdriver)

        profile_deletion_statements.enter_the_password(
            webdriver, profile_page_statements.account_password
        )
        profile_deletion_statements.confirm_the_deletion(webdriver)

        profile_deletion_statements.assert_the_session_ended_on_a_usable_page(webdriver)

    def test_should_refuse_a_wrong_password_without_ending_the_session(
        self, webdriver, app_url, profile_page_statements, profile_deletion_statements
    ):
        # A refused confirmation is not a session ending: the user stays on the screen with what
        # they typed, and the tokens are untouched.
        profile_page_statements.navigate_to_profile_page(webdriver, app_url)
        profile_deletion_statements.open_the_confirmation(webdriver)
        profile_deletion_statements.assert_the_confirm_button_is_disabled(webdriver)

        profile_deletion_statements.enter_the_password(webdriver, self.WRONG_PASSWORD)
        profile_deletion_statements.confirm_the_deletion(webdriver)

        profile_deletion_statements.assert_a_refusal_is_shown(webdriver)
        profile_page_statements.assert_the_header_shows(
            webdriver, profile_page_statements.account_email
        )

    def test_should_close_the_confirmation_on_cancel(
        self, webdriver, app_url, profile_page_statements, profile_deletion_statements
    ):
        profile_page_statements.navigate_to_profile_page(webdriver, app_url)
        profile_deletion_statements.open_the_confirmation(webdriver)

        profile_deletion_statements.cancel_the_deletion(webdriver)

        profile_deletion_statements.assert_the_confirmation_is_closed(webdriver)
