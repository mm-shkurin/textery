import pytest

from tests.frontend.abstract_frontend_test import AbstractFrontendTest

# RED 1.1 (analytical; live run deferred to green-selenium). In the current build, picking a
# document type routes to step='mode' and opens the mode-select modal (useFlowNavigation.selectType
# -> setStep('mode'); DocumentGenerationFlow renders FlowLanding's mode modal), so neither the
# generation breadcrumb nor the topic composer renders and assert_generation_surface_shown times
# out with a selenium TimeoutException. Story 18 drops the mode modal so picking a type lands
# directly on the composer. Un-skip + verify in green-selenium once the unified flow lands.


@pytest.mark.skip(
    reason="RED 1.1: picking a doklad type still opens the mode-select modal (step='mode') "
    "instead of landing on the generation composer — neither [data-testid='generation-breadcrumb'] "
    "nor [data-testid='topic-input'] renders, so assert_generation_surface_shown times out "
    "(selenium TimeoutException). Story 18 removes the mode modal and goes straight to generation."
)
class TestGenerateFlowAcceptance(AbstractFrontendTest):
    """UI Test Scenario 1.1: Selecting a type goes straight to generation.

    Given the user is on the create flow
    When they pick a document type
    Then generation starts immediately
    And no mode-select modal is shown

    "Immediately" is the removal of the mode step, not a POST at type-pick time: the composer
    is where the topic comes from, and there is nothing to generate before the user supplies
    one. So the type pick must land on the generation surface, and the send must start exactly
    one run.
    """

    TOPIC = "Влияние искусственного интеллекта на образование"

    def test_should_go_straight_to_generation_with_no_mode_modal(
        self, webdriver, app_url, generate_flow_statements
    ):
        generate_flow_statements.pick_document_type_for_doklad(webdriver, app_url)

        generate_flow_statements.assert_generation_surface_shown(webdriver)
        generate_flow_statements.assert_no_mode_modal_shown(webdriver)

        generate_flow_statements.send_topic(webdriver, self.TOPIC)

        generate_flow_statements.assert_exactly_one_generation_started(webdriver, self.TOPIC)
