from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestManualEditorLineBreakAcceptance(AbstractFrontendTest):
    """Bug: line break in Ручной режим (sprint criterion, 2026-07-20).

    Given the visitor is typing in the manual editor
    When the visitor presses Enter
    Then the text breaks onto a new line, exactly once per keystroke

    This is the live-browser proof the jsdom unit tests structurally cannot give. They reach
    the editor through a synthetic keyDown, which runs the keymap but never ProseMirror's own
    contenteditable input handling — so a double-insert (both paths firing) is invisible there.
    """

    def test_should_insert_exactly_one_break_per_enter_keystroke(
        self, webdriver, app_url, manual_editor_line_break_statements
    ):
        statements = manual_editor_line_break_statements
        statements.open_manual_editor_for_doklad(webdriver, app_url)

        statements.type_text_in_editor(webdriver, "foo")
        statements.press_enter_in_editor(webdriver)
        statements.continue_typing_in_editor(webdriver, "bar")

        statements.assert_break_count_is(webdriver, 1)
        statements.assert_editor_content_html_is(webdriver, "foo<br>bar")
        statements.assert_visual_line_count_is(webdriver, 2)

    def test_should_keep_both_breaks_when_enter_is_pressed_twice(
        self, webdriver, app_url, manual_editor_line_break_statements
    ):
        """Pins the behavior the premortem on `cffedc7` flagged as possibly broken.

        In jsdom, two consecutive Enters at end-of-content collapse to zero breaks. That was a
        fake-caret artifact, not a product defect: a real browser keeps both, and typing after
        them lands on the third line. Asserted here so the question stays answered.
        """
        statements = manual_editor_line_break_statements
        statements.open_manual_editor_for_doklad(webdriver, app_url)

        statements.type_text_in_editor(webdriver, "foo")
        statements.press_enter_in_editor(webdriver, times=2)
        statements.continue_typing_in_editor(webdriver, "baz")

        statements.assert_break_count_is(webdriver, 2)
        statements.assert_editor_content_html_is(webdriver, "foo<br><br>baz")
        statements.assert_visual_line_count_is(webdriver, 3)
