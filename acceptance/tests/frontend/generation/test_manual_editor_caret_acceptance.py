from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestManualEditorCaretTracksFormattingAcceptance(AbstractFrontendTest):
    """UI Test Scenario 3.2 (Track B owe): the toolbar reflects the CARET, not globally.

    Given the editor holds a bold run followed by a plain run
    When the visitor moves the caret (keyboard only, no drag) into the bold run
    Then the bold toolbar button shows active
    And when the caret moves into the plain run it shows inactive

    The jsdom test hand-fired the `select` event via `fireEvent.select`. Only a real browser
    proves a caret-only cursor move dispatches the selection event the toolbar listens for.
    """

    def test_should_track_bold_state_as_the_caret_moves_between_runs(
        self, webdriver, app_url, manual_editor_caret_statements
    ):
        statements = manual_editor_caret_statements
        statements.open_manual_editor_for_doklad(webdriver, app_url)

        statements.type_text_with_leading_bold_run(webdriver, "aaabbb", bold_len=3)

        # Visit the plain run FIRST — this drives the true->false edge and, crucially, resets the
        # button to false so the next step proves a genuine false->true CARET re-read rather than
        # a state inherited from the bold-apply.
        statements.move_caret_into_trailing_run(webdriver)
        statements.assert_bold_button_becomes_inactive(webdriver)

        # ...then move the caret INTO the bold run: the false->true edge scenario 3.2 most needs —
        # the toolbar activating because the caret ENTERED bold text, no drag, no selection.
        statements.move_caret_into_leading_run(webdriver)
        statements.assert_bold_button_becomes_active(webdriver)
