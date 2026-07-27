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


# RED (analytical, live run deferred to green-selenium): ExportControl receives only `documentId`
# (ManualEditor.tsx:164) — no dirty flag, no `save` — so a PDF click fires the export GET with NO
# preceding save PUT. The save-first ordering assertion fails: no save request is observed before
# the export. green-frontend threads the dirty flag + save into ExportControl; green-selenium
# removes this marker and runs it live.
class TestExportControlDirtyExportAcceptance(AbstractFrontendTest):
    """UI Test Scenario 4.1: Exporting with unsaved edits saves first.

    Given a document with unsaved edits open in the editor
    When the user triggers an export
    Then the edits are saved first (a save PUT fires before the export GET)
    """

    def test_should_save_before_exporting_when_editor_has_unsaved_edits(
        self, webdriver, app_url, export_control_statements
    ):
        export_control_statements.open_manual_editor_for_doklad(webdriver, app_url)

        export_control_statements.make_unsaved_edit(webdriver)

        export_control_statements.trigger_pdf_export_with_unsaved_edits(webdriver)

        export_control_statements.assert_export_saves_before_exporting(webdriver)
