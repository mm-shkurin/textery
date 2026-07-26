from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestManualEditorListAcceptance(AbstractFrontendTest):
    """Editor Extension E2.1: bulleted and numbered lists round-trip.

    Given the editor with a bulleted list and a numbered list
    When the document is saved and reloaded
    Then both lists return as the correct semantic elements

    The jsdom test proved the toolbar wraps a block in a list node; this proves a
    browser-built list survives the backend's store-and-reload.
    """

    def test_should_round_trip_bulleted_and_numbered_lists(
        self, webdriver, app_url, manual_editor_list_statements
    ):
        statements = manual_editor_list_statements
        statements.open_manual_editor_for_doklad(webdriver, app_url)

        statements.build_bulleted_and_numbered_lists(webdriver)

        statements.save_document(webdriver)

        statements.assert_saved_lists_round_trip_as_semantic_html(webdriver)
