from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestProfileAvatarUploadAcceptance(AbstractFrontendTest):
    """UI: choosing a picture uploads it and shows it; removing it puts the initials back.

    Given a signed-in visitor on their profile screen
    When they choose a non-square photograph
    Then it is accepted and displayed, and can then be removed
    """

    def test_should_accept_a_photograph_and_show_it(
        self, webdriver, app_url, profile_page_statements, profile_avatar_statements
    ):
        # A real, decodable PNG, and NON-SQUARE: the client crops a centred square out of it and
        # downscales before uploading, and a source the browser cannot decode never gets that far.
        profile_page_statements.navigate_to_profile_page(webdriver, app_url)

        profile_avatar_statements.choose_a_photograph(webdriver)

        profile_avatar_statements.assert_no_rejection_is_shown(webdriver)
        profile_avatar_statements.assert_the_picture_is_shown(webdriver)

    def test_should_put_the_initials_back_when_the_picture_is_removed(
        self, webdriver, app_url, profile_page_statements, profile_avatar_statements
    ):
        profile_page_statements.navigate_to_profile_page(webdriver, app_url)
        profile_avatar_statements.choose_a_photograph(webdriver)
        profile_avatar_statements.assert_the_picture_is_shown(webdriver)

        profile_avatar_statements.remove_the_picture(webdriver)

        profile_avatar_statements.assert_no_picture_is_shown(webdriver)
