import pytest

from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestManualEditorAcceptance(AbstractFrontendTest):
    """UI Test Scenario 1.2: Selecting Ручной режим opens the empty editor.

    Given the mode modal is open
    When the visitor selects "Ручной режим"
    Then the mode modal closes
    And an empty editor opens, scoped to the chosen document type
    """

    def test_should_open_manual_editor_scoped_to_document_type(
        self, webdriver, app_url, manual_editor_statements
    ):
        manual_editor_statements.open_manual_editor_for_doklad(webdriver, app_url)

        manual_editor_statements.assert_mode_modal_is_closed(webdriver)
        manual_editor_statements.assert_manual_editor_is_open_for_doklad(webdriver)
