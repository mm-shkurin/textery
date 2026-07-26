import pytest

from tests.frontend.abstract_frontend_test import AbstractFrontendTest


# RED: scenario 1.1 — the editor has no export control yet. The editor opens fine (live session),
# but `[data-testid='export-control-trigger']` does not exist, so opening the control times out.
# Un-skip in green-selenium once the export control (trigger + PDF/DOCX choices) is implemented.
@pytest.mark.skip(reason="RED: export control not implemented (scenario 1.1)")
class TestExportControlDisplayAcceptance(AbstractFrontendTest):
    """UI Test Scenario 1.1: The editor offers a PDF and a DOCX export choice.

    Given a document open in the editor
    When the user opens the export control
    Then a PDF choice and a DOCX choice are shown
    """

    def test_should_offer_pdf_and_docx_export_choices(
        self, webdriver, app_url, export_control_statements
    ):
        export_control_statements.open_manual_editor_for_doklad(webdriver, app_url)

        export_control_statements.open_export_control(webdriver)

        export_control_statements.assert_pdf_and_docx_choices_are_shown(webdriver)
