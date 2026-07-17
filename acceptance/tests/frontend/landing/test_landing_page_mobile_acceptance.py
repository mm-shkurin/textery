from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from tests.frontend.abstract_frontend_test import AbstractFrontendTest

HEADER_PRIMARY_CTA_BUTTON = (By.CSS_SELECTOR, "[data-testid='header-primary-cta-button']")
TYPE_MODAL = (By.CSS_SELECTOR, "[data-testid='type-modal']")
WAIT_TIMEOUT_SECONDS = 5


def _given_signed_in(driver) -> None:
    """Seed a session so the landing CTA opens the flow.

    The gate checks only that a token is PRESENT, so a placeholder satisfies it. This scenario
    is about viewport overflow, not auth; driving three auth screens to reach a modal would make
    a layout test fail whenever sign-in breaks. When the backend starts requiring
    `Authorization`, this must become a real sign-in.
    """
    driver.execute_script(
        "window.sessionStorage.setItem('textery.auth.accessToken', 'acceptance-test-token');"
        "window.sessionStorage.setItem('textery.auth.refreshToken', 'acceptance-test-token');"
    )
    driver.refresh()


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
        # Story 7 put everything behind the landing behind a session: the CTA now sends an
        # anonymous visitor to /login instead of opening the type modal, so a session is a
        # precondition of reaching the modal at all. The landing itself stays public — the test
        # above asserts exactly that and needs no session.
        _given_signed_in(mobile_webdriver)
        WebDriverWait(mobile_webdriver, WAIT_TIMEOUT_SECONDS).until(
            ec.element_to_be_clickable(HEADER_PRIMARY_CTA_BUTTON)
        ).click()
        WebDriverWait(mobile_webdriver, WAIT_TIMEOUT_SECONDS).until(ec.visibility_of_element_located(TYPE_MODAL))

        responsive_statements.assert_no_horizontal_overflow(mobile_webdriver, "the document-type modal")
