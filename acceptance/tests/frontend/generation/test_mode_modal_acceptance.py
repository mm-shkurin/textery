import pytest

from tests.frontend.abstract_frontend_test import AbstractFrontendTest


@pytest.mark.skip(
    reason="RED: AssertionError: expected manual mode card to not have 'disabled' class "
    "(ModeModal.tsx still marks 'manual' as available: false)"
)
class TestModeModalAcceptance(AbstractFrontendTest):
    """UI Test Scenario 1.1: The mode modal now shows both modes as available.

    Given the mode modal is open, reached via the document-type modal
    Then "Ручной режим" and "Автоматический режим" cards are both shown as available
      and selectable
    And neither card shows a "скоро" badge
    """

    def test_should_show_both_mode_cards_as_available(self, webdriver, app_url, mode_modal_statements):
        mode_modal_statements.navigate_to_mode_modal(webdriver, app_url)

        mode_modal_statements.assert_manual_mode_card_is_available_and_selectable(webdriver)
        mode_modal_statements.assert_auto_mode_card_is_available_and_selectable(webdriver)
        mode_modal_statements.assert_no_card_shows_soon_badge(webdriver)
