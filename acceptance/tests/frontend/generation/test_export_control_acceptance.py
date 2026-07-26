from tests.frontend.abstract_frontend_test import AbstractFrontendTest


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
