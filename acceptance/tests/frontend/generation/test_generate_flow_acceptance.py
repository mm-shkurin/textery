import pytest

from tests.frontend.abstract_frontend_test import AbstractFrontendTest

# 1.1 live run is deferred to green-selenium: it needs a running backend (the flow issues a real
# register -> verify -> login round trip, then a real generation POST) plus a browser, neither of
# which the analytical phases have. The RED prediction this skip originally carried — a
# TimeoutException from assert_generation_surface_shown because selectType routed to step='mode' —
# is spent: useFlowNavigation.selectType now sets step='form' with mode='auto' and the mode modal
# is gone, so the failure it named can no longer be produced. Un-skip in green-selenium.


@pytest.mark.skip(
    reason="1.1 needs a live backend + browser, so the run is deferred to green-selenium. The "
    "unified flow has landed (selectType -> step='form', mode='auto', no mode modal), so no "
    "analytical failure is predicted; if the live stack is unhealthy the first failure will be "
    "assert_reached_generation_workspace, whose AssertionError names the current URL so an "
    "auth-collapse back to the landing is not misread as a routing regression."
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

        generate_flow_statements.assert_reached_generation_workspace(webdriver)
        generate_flow_statements.assert_generation_surface_shown(webdriver)
        generate_flow_statements.assert_no_mode_modal_shown(webdriver)
        generate_flow_statements.assert_no_generation_started_yet(webdriver)

        generate_flow_statements.send_topic(webdriver, self.TOPIC)

        generate_flow_statements.assert_exactly_one_generation_started(webdriver, self.TOPIC)
