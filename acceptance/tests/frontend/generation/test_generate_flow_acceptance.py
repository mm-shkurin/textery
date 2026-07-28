from tests.frontend.abstract_frontend_test import AbstractFrontendTest

# 1.1's live run happened in green-selenium against a running backend + browser. The RED
# prediction this test once carried — a TimeoutException from assert_generation_surface_shown
# because selectType routed to step='mode' — was already spent when the skip was lifted:
# useFlowNavigation.selectType has set step='form' with mode='auto' since 916ab0a and the mode
# modal is deleted, so green-selenium was a first live verification of shipped behaviour rather
# than a red-to-green transition.
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

        generate_flow_statements.assert_send_started_a_run(webdriver)
        generate_flow_statements.assert_exactly_one_generation_started(webdriver, self.TOPIC)
