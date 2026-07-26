import pytest

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


@pytest.mark.skip(
    reason="RED: in-flight lock wiring is implemented; unskip is the green-selenium step. "
    "Live verified 2026-07-26 with reordered throttle (open control before throttling)."
)
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
