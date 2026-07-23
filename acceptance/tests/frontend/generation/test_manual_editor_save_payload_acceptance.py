from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestManualEditorSavePayloadAcceptance(AbstractFrontendTest):
    """Track B owe: the SAVE half of the line-break behavior (data-loss shaped).

    Given the visitor typed text, pressed Enter, and typed more
    When the visitor saves the document
    Then the line break survives the save round-trip through the backend

    The line-break Selenium test proved only that a real browser RENDERS one break per Enter.
    It never proved the break reaches the PUT body via `editor.getHTML()` or survives the
    backend's store-and-reload — a sanitizer or parse rule could drop it, and the user would
    reopen paragraphs run together. This reads the saved document back through the backend's own
    GET, the true round-trip a reopen takes.
    """

    def test_should_persist_the_line_break_through_a_save_round_trip(
        self, webdriver, app_url, manual_editor_save_payload_statements
    ):
        statements = manual_editor_save_payload_statements
        statements.open_manual_editor_for_doklad(webdriver, app_url)

        statements.type_text_in_editor(webdriver, "foo")
        statements.press_enter_in_editor(webdriver)
        statements.continue_typing_in_editor(webdriver, "bar")

        statements.save_document(webdriver)

        statements.assert_saved_content_preserves_single_break(webdriver)
