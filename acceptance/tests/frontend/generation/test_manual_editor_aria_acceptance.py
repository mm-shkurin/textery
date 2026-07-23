from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestManualEditorAriaAnnouncedAcceptance(AbstractFrontendTest):
    """Track B owe: the a11y surfaces jsdom pins but cannot evaluate.

    The editor's role/aria-multiline/aria-placeholder and the link button's aria-expanded
    highlight all render in the DOM under jsdom, but jsdom computes no accessibility tree and
    applies no CSS. A real browser is the only place the COMPUTED textbox role and the painted
    highlight are observable.
    """

    def test_should_compute_a_multiline_textbox_role_on_the_editor(
        self, webdriver, app_url, manual_editor_aria_statements
    ):
        manual_editor_aria_statements.open_manual_editor_for_doklad(webdriver, app_url)

        manual_editor_aria_statements.assert_editor_announces_multiline_textbox(webdriver)


class TestManualEditorLinkButtonHighlightAcceptance(AbstractFrontendTest):
    """Track B owe: the aria-expanded highlight rule (jsdom applies no CSS).

    Given the cursor is outside any link
    When the link popover opens
    Then the link toolbar button highlights — driven only by aria-expanded, not aria-pressed
    """

    def test_should_highlight_link_button_while_popover_is_open(
        self, webdriver, app_url, manual_editor_aria_statements
    ):
        manual_editor_aria_statements.open_manual_editor_for_doklad(webdriver, app_url)

        manual_editor_aria_statements.assert_link_button_highlights_while_popover_open(webdriver)
