from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestManualEditorAutosaveAcceptance(AbstractFrontendTest):
    """Editor Extension E3.1: edits autosave without an explicit click.

    Given a document open with unsaved edits
    When the user stops typing past the debounce interval
    Then the edits are saved automatically
    And a saved indicator is shown

    The jsdom test proved the debounce timer under mocks; this proves a real browser
    fires the PUT and the backend stores it, with no click on Сохранить.
    """

    def test_should_autosave_edits_without_clicking_save(
        self, webdriver, app_url, manual_editor_autosave_statements
    ):
        statements = manual_editor_autosave_statements
        statements.open_manual_editor_for_doklad(webdriver, app_url)

        statements.type_text_in_editor(webdriver, "autosaved text")

        statements.assert_editor_autosaves_without_a_click(webdriver)

        statements.assert_autosaved_content_persisted(webdriver, "<p>autosaved text</p>")
