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


class TestManualEditorEmptyStateAcceptance(AbstractFrontendTest):
    """UI Test Scenario 2.1: A freshly created document shows an empty, ready-to-type editor.

    Given a visitor has just created a manual document
    Then the editor shows an empty content area with a placeholder, not a loading skeleton
    And the formatting toolbar is visible with heading, paragraph, list, bold, and italic
      controls
    And the breadcrumb shows the chosen document type and "Ручной режим"
    """

    def test_should_show_empty_editor_with_placeholder_and_toolbar(
        self, webdriver, app_url, manual_editor_statements
    ):
        manual_editor_statements.open_manual_editor_for_doklad(webdriver, app_url)

        manual_editor_statements.assert_no_loading_skeleton_is_shown(webdriver)
        manual_editor_statements.assert_content_placeholder_is_visible(webdriver)
        manual_editor_statements.assert_toolbar_controls_are_visible(webdriver)
        manual_editor_statements.assert_manual_editor_is_open_for_doklad(webdriver)
