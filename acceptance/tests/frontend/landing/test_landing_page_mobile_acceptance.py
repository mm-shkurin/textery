from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from tests.frontend.abstract_frontend_test import AbstractFrontendTest

HEADER_PRIMARY_CTA_BUTTON = (By.CSS_SELECTOR, "[data-testid='header-primary-cta-button']")
TYPE_MODAL = (By.CSS_SELECTOR, "[data-testid='type-modal']")
WAIT_TIMEOUT_SECONDS = 5


class TestLandingPageMobileAcceptance(AbstractFrontendTest):
    """UI Test Scenario: the landing page and its "create generation" modal fit a
    phone-width viewport without introducing horizontal scroll.

    Given a visitor opens the landing page on a 390px-wide (iPhone-class) viewport
    Then the page does not overflow horizontally
    And opening the document-type modal does not overflow horizontally either
    """

    def test_should_not_overflow_horizontally_on_landing(
        self, mobile_webdriver, app_url, landing_page_statements, responsive_statements
    ):
        landing_page_statements.navigate_to_landing_page(mobile_webdriver, app_url)

        responsive_statements.assert_no_horizontal_overflow(mobile_webdriver, "the landing page")

    def test_should_not_overflow_horizontally_on_type_modal(
        self, mobile_webdriver, app_url, landing_page_statements, responsive_statements
    ):
        landing_page_statements.navigate_to_landing_page(mobile_webdriver, app_url)
        WebDriverWait(mobile_webdriver, WAIT_TIMEOUT_SECONDS).until(
            ec.element_to_be_clickable(HEADER_PRIMARY_CTA_BUTTON)
        ).click()
        WebDriverWait(mobile_webdriver, WAIT_TIMEOUT_SECONDS).until(ec.visibility_of_element_located(TYPE_MODAL))

        responsive_statements.assert_no_horizontal_overflow(mobile_webdriver, "the document-type modal")
