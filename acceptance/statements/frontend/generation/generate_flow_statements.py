from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from statements.frontend.base_frontend_statements import BaseFrontendStatements, WAIT_TIMEOUT_SECONDS
from statements.frontend.generation.mode_modal_statements import MODE_MODAL

# Story 18 unifies the create flow: picking a document type no longer opens a mode-select
# modal, it goes STRAIGHT to generation. The generating surface is marked by this testid,
# which is also scenario 1.2's subject ("a generating state is shown"). Green implements it.
GENERATING_STATE = (By.CSS_SELECTOR, "[data-testid='generation-generating']")


class GenerateFlowStatements(BaseFrontendStatements):
    """Selenium DSL for the unified create flow (story 18, scenario 1.1).

    Picking a document type must land directly on the generating state, with the
    story-5-era mode-select modal removed from the path entirely.
    """

    def pick_document_type_for_doklad(self, driver: WebDriver, app_url: str) -> None:
        # navigate_to_doklad_type_modal is the shared "click the CTA, then pick the doklad
        # type card" entry point — exactly the spec's "When they pick a document type". A live
        # session is required because starting generation POSTs /api/v1/generations, which the
        # backend answers with 401 for a seeded token (collapsing the flow to the landing).
        self.navigate_to_doklad_type_modal(driver, app_url, live_session=True)

    def assert_generation_started(self, driver: WebDriver) -> None:
        element = self._wait_for_visible(driver, GENERATING_STATE)
        assert element.is_displayed(), "expected the generating state to be shown after picking a type"

    def assert_no_mode_modal_shown(self, driver: WebDriver) -> None:
        WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(
            ec.invisibility_of_element_located(MODE_MODAL),
            "expected no mode-select modal after picking a type, but it was shown",
        )
