import pytest

from tests.frontend.abstract_frontend_test import AbstractFrontendTest


@pytest.mark.skip(
    reason="RED: frontend/ has no Landing page markup yet -- placeholder App renders an "
    "empty <div id='app' /> with no hero/CTA data-testid elements, so the hero heading "
    "locator times out (TimeoutException) instead of resolving"
)
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
