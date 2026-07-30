from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestManualEditorBlockSchemaAcceptance(AbstractFrontendTest):
    """Editor Extension E1.1: multi-paragraph block content round-trips (block schema).

    Given the editor with block content: paragraphs, H1, H2, H3
    When the document is saved and reloaded
    Then each block returns as its correct semantic element

    The jsdom migration proved serialize output; this proves the live browser build survives
    the backend's own store-and-reload, the round-trip a real reopen takes.
    """

    def test_should_round_trip_multi_block_content_as_semantic_html(
        self, webdriver, app_url, manual_editor_block_schema_statements
    ):
        statements = manual_editor_block_schema_statements
        statements.open_manual_editor_for_doklad(webdriver, app_url)

        statements.build_multi_block_document(webdriver)

        statements.save_document(webdriver)

        statements.assert_saved_blocks_round_trip_as_semantic_html(webdriver)
