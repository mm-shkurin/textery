import pytest

from tests.frontend.abstract_frontend_test import AbstractFrontendTest

# RED 1.1 (analytical; live run deferred to green-selenium). In the current build, picking a
# document type routes to step='mode' and opens the mode-select modal (useFlowNavigation.selectType
# -> setStep('mode'); DocumentGenerationFlow renders FlowLanding's mode modal). Generation does not
# start, so no [data-testid='generation-generating'] surface exists — assert_generation_started
# times out on _wait_for_visible with a selenium TimeoutException. Story 18 drops the mode modal so
# picking a type goes straight to the generating state. Un-skip + verify RED, then green in
# green-selenium once the unified flow lands.


@pytest.mark.skip(
    reason="RED 1.1: picking a doklad type still opens the mode-select modal (step='mode') "
    "instead of starting generation — no [data-testid='generation-generating'] surface renders, "
    "so assert_generation_started times out (selenium TimeoutException). Story 18 removes the "
    "mode modal and goes straight to generation."
)
class TestGenerateFlowAcceptance(AbstractFrontendTest):
    """UI Test Scenario 1.1: Selecting a type goes straight to generation.

    Given the user is on the create flow
    When they pick a document type
    Then generation starts immediately
    And no mode-select modal is shown
    """

    def test_should_go_straight_to_generation_with_no_mode_modal(
        self, webdriver, app_url, generate_flow_statements
    ):
        generate_flow_statements.pick_document_type_for_doklad(webdriver, app_url)

        generate_flow_statements.assert_generation_started(webdriver)
        generate_flow_statements.assert_no_mode_modal_shown(webdriver)
