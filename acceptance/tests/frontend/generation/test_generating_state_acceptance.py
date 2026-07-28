import pytest

from tests.frontend.abstract_frontend_test import AbstractFrontendTest


# green-selenium removes this marker only — there is no production change owed, and the reason
# is recorded rather than predicted because this contract was run live during red-selenium.
#
# NOT a red-to-green transition. The subject of this scenario — data-testid='generation-generating'
# on DocArea's pending branch — was added by scenario 1.1's green-frontend explicitly for 1.2, so
# the behaviour ships already and the honest RED prediction was spent before it was written. Three
# consecutive live runs pass (10.9s / 12.8s / 12.0s) against the per-worktree stack.
#
# What the RED protocol did buy, both found by running it rather than reasoning about it, and both
# invisible to the renderer-level suite:
#   1. `.chat-panel h3` carries `text-transform: uppercase`, and Selenium reports RENDERED text —
#      the panel reads `ХОД ГЕНЕРАЦИИ`, not the source's `Ход генерации`. jsdom applies no CSS, so
#      this layer is the only one that can see it.
#   2. `Progress.ChatMsg` puts its `✦` avatar on its own line in `.text`, so the panel's visible
#      text is not the copy the component source reads.
# The first prediction named the right assertion and the right failure type for the right reason
# (the panel value was guessed, the doc-surface value was read off the component and held).
@pytest.mark.skip(
    reason="green-selenium is remove-marker-only; verified live in red-selenium, see the note above"
)
class TestGeneratingStateAcceptance(AbstractFrontendTest):
    """UI Test Scenario 1.2: A generating document shows progress.

    Given the user has started a generation
    When the result is not ready yet
    Then a generating state is shown

    "The result is not ready yet" is produced by holding the network, not by hoping the
    backend is slow: the acceptance stack's fake provider answers instantly, so the pending
    state is otherwise a few milliseconds wide and a wait on it is a coin flip whose loss
    looks exactly like a regression. See `hold_the_result_not_ready`.
    """

    TOPIC = "Влияние искусственного интеллекта на образование"

    def test_should_show_a_generating_state_while_the_result_is_not_ready(
        self, webdriver, app_url, generating_state_statements
    ):
        generating_state_statements.pick_document_type_for_doklad(webdriver, app_url)
        generating_state_statements.hold_the_result_not_ready(webdriver)

        generating_state_statements.send_topic(webdriver, self.TOPIC)

        generating_state_statements.assert_send_started_a_run(webdriver)
        generating_state_statements.assert_no_result_shown(webdriver)
        generating_state_statements.assert_generating_state_shown(webdriver)
        generating_state_statements.assert_client_is_awaiting_the_result(webdriver)

        generating_state_statements.release_the_result(webdriver)
