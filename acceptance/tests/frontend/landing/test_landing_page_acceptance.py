from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestLandingPageAcceptance(AbstractFrontendTest):
    """UI Test Scenario 1.1: The landing page displays the hero and primary CTA.

    Given a visitor opens the landing page
    Then the "Word онлайн" hero heading and subheading are visible
    And a "Создать генерацию" call-to-action button is visible
    """

    def test_should_display_hero_and_primary_cta(self, webdriver, app_url, landing_page_statements):
        landing_page_statements.navigate_to_landing_page(webdriver, app_url)

        landing_page_statements.assert_hero_heading_is_visible(webdriver)
        landing_page_statements.assert_hero_subheading_is_visible(webdriver)
        landing_page_statements.assert_primary_cta_button_is_visible(webdriver)
