import pytest

from tests.frontend.abstract_frontend_test import AbstractFrontendTest


# RED, analytical. The live run is deferred to green-selenium: this worktree's per-worktree stack
# (compose project `textery-fe`, BACKEND_PORT=8100 exported, FRONTEND_PORT deliberately not, npm
# run dev on 5173) has to be standing for any of it to mean anything, and this contract cannot go
# green until several layers below it land.
#
# PREDICTED FAILURE — TimeoutException from `assert_editor_opened_by_itself`, on
# `[data-testid='manual-editor']`, with the message "expected a completed generation to become
# the editor by itself, but [data-testid='manual-editor'] never appeared within 30s".
#
# WHY, read off the code rather than guessed:
#   * `useGeneration.runPollAttempt` (useGeneration.ts) handles `status === 'completed'` by
#     setting content + state='completed'. It does nothing else — there is no conversion call
#     and no navigation.
#   * `DocArea.tsx` renders the `completed` branch as a read-only markdown view
#     (`data-testid='doc-body'`) with a "Создать новый доклад" button. That is the surface a
#     finished generation lands on today.
#   * `DocumentGenerationFlow.tsx` mounts `ManualEditor` only for `mode === 'manual'`, and
#     `useFlowNavigation.selectType` sets `mode='auto'` for the whole create path. So no state
#     the create flow can reach renders the editor at all.
#   * `POST /api/v1/documents/from-generation` — the endpoint the story's own endpoints.md names
#     as the ONLY new one — exists nowhere: not in `backend/`, not in `frontend/src`. There is no
#     conversion to trigger.
# So the run completes, `doc-body` comes up, `manual-editor` never does, and the wait expires.
# `assert_the_read_only_result_was_replaced` would fail second (doc-body IS shown) and
# `assert_editor_holds_the_generated_text` third; the first wait is what the run reports.
@pytest.mark.skip(reason="RED: predicted TimeoutException — see the recorded prediction above")
class TestAutoEditorTransitionAcceptance(AbstractFrontendTest):
    """UI Test Scenario 2.1: A completed generation opens automatically in the editor.

    Given the user is watching a generation complete
    When the text becomes ready
    Then the surface becomes the editor with the generated content loaded
    And the user made no extra click to get there

    Throttled, but only across ONE step, and the boundary is the point. 2.1's SUBJECT is the
    terminal state — once the editor is up it stays up, so waiting for it is not a race and it
    pays no latency. 2.1's INSTRUMENT is not terminal at all: the gesture watch has to be armed
    while the run is still pending, and against the acceptance stack's zero-latency fake provider
    that window is exactly as transient as 1.2's subject was. So the create POST is held open for
    the arm (`hold_the_run_pending`) and the latency is dropped again the moment the watch is
    live (`let_the_run_finish`), leaving the transition itself and the ManualEditor chunk fetch
    unthrottled.

    "Watching a generation complete" is therefore established twice over: the composer is gone
    (`assert_send_started_a_run`) AND the generating surface is up at arm time — the second is
    what makes an empty event list evidence rather than an artifact of arming too late.
    """

    TOPIC = "Влияние искусственного интеллекта на образование"

    def test_should_open_the_completed_generation_in_the_editor_with_no_extra_click(
        self, webdriver, app_url, auto_editor_transition_statements
    ):
        auto_editor_transition_statements.pick_document_type_for_doklad(webdriver, app_url)

        auto_editor_transition_statements.hold_the_run_pending(webdriver)
        auto_editor_transition_statements.send_topic(webdriver, self.TOPIC)
        auto_editor_transition_statements.assert_send_started_a_run(webdriver)
        auto_editor_transition_statements.watch_for_any_further_user_gesture(webdriver)
        auto_editor_transition_statements.let_the_run_finish(webdriver)

        auto_editor_transition_statements.assert_editor_opened_by_itself(webdriver)
        auto_editor_transition_statements.assert_the_read_only_result_was_replaced(webdriver)
        auto_editor_transition_statements.assert_editor_holds_the_generated_text(webdriver)

        # The wire half, and it is not decoration: the two defects that hurt most here leave no
        # mark on screen. A poll loop that outlived its result keeps hitting the backend every
        # 5s behind a perfectly correct-looking editor, and a conversion driven off those ticks
        # creates one duplicate document per tick — the user sees one editor and finds four to
        # nine identical documents later. Asserted last because both need the editor to be up.
        auto_editor_transition_statements.assert_the_conversion_created_exactly_one_document(
            webdriver
        )
        auto_editor_transition_statements.assert_the_poll_loop_stopped(webdriver)
