from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestProfileRenameAcceptance(AbstractFrontendTest):
    """UI: renaming the account updates the header without a page reload.

    Given a signed-in visitor on their profile screen
    When they type a display name and save it
    Then the profile card and the account menu both show it, with no reload
    """

    NEW_NAME = "Ада Лавлейс"

    def test_should_show_the_new_name_in_the_header_without_a_reload(
        self, webdriver, app_url, profile_page_statements
    ):
        # No reload anywhere in this test, deliberately. PATCH answers with the whole profile so
        # the client can update its identity snapshot from that response; a test that refreshed
        # first would pass against a client that only ever learns the name from a fresh GET.
        profile_page_statements.navigate_to_profile_page(webdriver, app_url)

        profile_page_statements.enter_name(webdriver, self.NEW_NAME)
        profile_page_statements.save_the_name(webdriver)

        profile_page_statements.assert_the_screen_shows_the_name(webdriver, self.NEW_NAME)
        profile_page_statements.assert_the_header_shows(webdriver, self.NEW_NAME)

    def test_should_leave_the_field_holding_the_normalized_value_it_stored(
        self, webdriver, app_url, profile_page_statements
    ):
        # The stored value is trimmed, so the field must hold the trimmed one afterwards --
        # otherwise the form stays "unsaved" forever after a successful save.
        profile_page_statements.navigate_to_profile_page(webdriver, app_url)

        profile_page_statements.enter_name(webdriver, "  Ада Лавлейс  ")
        profile_page_statements.save_the_name(webdriver)

        profile_page_statements.assert_the_name_field_holds(webdriver, self.NEW_NAME)
        profile_page_statements.assert_the_save_button_is_disabled(webdriver)
