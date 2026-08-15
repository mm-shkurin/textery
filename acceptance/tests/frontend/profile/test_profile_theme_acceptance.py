from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestProfileThemeAcceptance(AbstractFrontendTest):
    """UI: the theme switch changes the page, and the choice survives a reload.

    Given a signed-in visitor with the account menu open
    When they use the theme switch
    Then the page changes theme, the menu stays open, and a reload keeps the choice
    """

    def test_should_switch_the_theme_and_keep_the_menu_open(
        self, webdriver, app_url, profile_page_statements, profile_theme_statements
    ):
        # The menu deliberately stays open: this item changes the page underneath it, and closing
        # would hide the result of the click behind the side effect of that same click.
        profile_page_statements.navigate_to_profile_page(webdriver, app_url)
        profile_page_statements.open_the_account_menu(webdriver)
        before = profile_theme_statements.read_theme(webdriver)

        profile_theme_statements.toggle_the_theme(webdriver)

        profile_theme_statements.assert_the_theme_is(
            webdriver, "light" if before == "dark" else "dark"
        )
        profile_theme_statements.assert_the_menu_stayed_open(webdriver)

    def test_should_keep_the_chosen_theme_after_a_reload(
        self, webdriver, app_url, profile_page_statements, profile_theme_statements
    ):
        # The stored choice is read before the first paint by the inline boot script. A theme
        # resolved after mount would show one frame of the wrong one on every load.
        profile_page_statements.navigate_to_profile_page(webdriver, app_url)
        profile_page_statements.open_the_account_menu(webdriver)
        before = profile_theme_statements.read_theme(webdriver)
        profile_theme_statements.toggle_the_theme(webdriver)
        chosen = "light" if before == "dark" else "dark"
        profile_theme_statements.assert_the_theme_is(webdriver, chosen)

        profile_theme_statements.reload(webdriver)

        profile_theme_statements.assert_the_theme_is(webdriver, chosen)
