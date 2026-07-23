from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestManualEditorPlaceholderDeleteAcceptance(AbstractFrontendTest):
    """Track B owe: the placeholder RETURNS after a real delete-to-empty (premortem owe).

    Given the visitor typed text with a hard break (Enter) and then deleted all of it
    When the editor is truly empty again
    Then the placeholder returns — data-placeholder, is-editor-empty, and the ::before paint

    The jsdom roundtrip test clears via `textContent = ''`, a DOM wipe that never runs the real
    delete transaction. A real select-all + Backspace after an Enter (a real hardBreak node)
    could leave a residual node so the emptiness-keyed placeholder would not return, leaving a
    blank unlabelled box. Only a live browser exercises that path.
    """

    def test_should_restore_placeholder_after_deleting_all_content(
        self, webdriver, app_url, manual_editor_placeholder_delete_statements
    ):
        statements = manual_editor_placeholder_delete_statements
        statements.open_manual_editor_for_doklad(webdriver, app_url)

        statements.type_text_in_editor(webdriver, "foo")
        statements.press_enter_in_editor(webdriver)
        statements.continue_typing_in_editor(webdriver, "bar")

        # Proves the typing actually landed: without this the whole test could false-pass on a
        # no-op keystroke (editor stays empty from mount, the final assertion passes trivially,
        # and the delete-then-return round-trip is never exercised).
        statements.assert_content_placeholder_is_hidden(webdriver)

        statements.clear_all_via_backspace(webdriver)

        statements.assert_content_placeholder_is_visible(webdriver)
