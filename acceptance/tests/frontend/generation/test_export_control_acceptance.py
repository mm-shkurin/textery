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


class TestExportControlInFlightAcceptance(AbstractFrontendTest):
    """UI Test Scenario 2.1: The export control is disabled while a request is in flight.

    Given a document open in the editor
    When the user triggers export and clicks again before it returns
    Then only one export request is sent
    """

    def test_should_send_only_one_export_request_on_double_click(
        self, webdriver, app_url, export_control_statements
    ):
        export_control_statements.open_manual_editor_for_doklad(webdriver, app_url)

        export_control_statements.trigger_export_as_pdf_twice(webdriver)

        export_control_statements.assert_exactly_one_export_request_was_sent(webdriver)


class TestExportControlProgressAcceptance(AbstractFrontendTest):
    """UI Test Scenario 3.1: An in-flight export shows a progress state.

    Given the user has triggered an export
    When the file is still being generated
    Then an exporting indicator is shown
    """

    def test_should_show_exporting_indicator_while_in_flight(
        self, webdriver, app_url, export_control_statements
    ):
        export_control_statements.open_manual_editor_for_doklad(webdriver, app_url)

        export_control_statements.trigger_throttled_pdf_export(webdriver)

        export_control_statements.assert_exporting_indicator_is_shown(webdriver)


class TestExportControlErrorAcceptance(AbstractFrontendTest):
    """UI Test Scenario 3.2: A failed export shows an inline error with retry, document unchanged.

    Given the user has triggered an export
    When the request fails
    Then an inline error with a retry is shown
    And the document view is unchanged
    """

    def test_should_show_inline_error_with_retry_and_leave_document_unchanged(
        self, webdriver, app_url, export_control_statements
    ):
        export_control_statements.open_manual_editor_for_doklad(webdriver, app_url)

        export_control_statements.trigger_failed_pdf_export(webdriver)

        export_control_statements.assert_export_error_with_retry_is_shown(webdriver)
        export_control_statements.assert_document_view_is_unchanged(webdriver)
