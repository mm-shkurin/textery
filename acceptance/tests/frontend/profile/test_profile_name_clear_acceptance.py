from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestProfileNameClearAcceptance(AbstractFrontendTest):
    """UI: clearing the name is a save, not a refusal.

    Given a signed-in visitor whose account has a display name
    When they empty the field and save
    Then the account falls back to showing its email address
    """

    NAME = "Ада Лавлейс"

    def test_should_fall_back_to_the_email_when_the_name_is_cleared(
        self, webdriver, app_url, profile_page_statements
    ):
        # Clearing is the documented way to remove a name, so it must answer 200 and change the
        # identity -- not a 400 on an empty field.
        profile_page_statements.navigate_to_profile_page(webdriver, app_url)
        profile_page_statements.enter_name(webdriver, self.NAME)
        profile_page_statements.save_the_name(webdriver)
        profile_page_statements.assert_the_screen_shows_the_name(webdriver, self.NAME)

        profile_page_statements.clear_the_name_field(webdriver)
        profile_page_statements.save_the_name(webdriver)

        profile_page_statements.assert_the_header_shows(
            webdriver, profile_page_statements.account_email
        )
        profile_page_statements.assert_the_counter_reads(webdriver, "0 / 60")
