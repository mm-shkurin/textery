from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestManualEditorLinkPopoverClipAcceptance(AbstractFrontendTest):
    """UI Test Scenario 7.9 (Track B owe): the link popover must not be clipped.

    Given the link popover is open
    Then it is fully visible — within the editor shell (which has overflow:hidden) and the
      viewport — so the URL field and both actions are reachable

    `.me-link-popover` is z-index:20 inside `.me-editor-shell { overflow:hidden }`; a z-index
    cannot escape an ancestor's clip. Only a real browser's layout can prove whether the 260px
    popover, anchored to a link button that sits near the toolbar's right edge, runs off the shell.
    """

    def test_should_open_the_link_popover_fully_within_the_shell(
        self, webdriver, app_url, manual_editor_popover_clip_statements
    ):
        statements = manual_editor_popover_clip_statements
        statements.open_manual_editor_for_doklad(webdriver, app_url)

        statements.open_link_popover(webdriver)

        statements.assert_popover_not_clipped(webdriver)

    def test_should_keep_the_link_popover_unclipped_on_a_narrow_viewport(
        self, webdriver, app_url, manual_editor_popover_clip_statements
    ):
        statements = manual_editor_popover_clip_statements
        statements.open_manual_editor_for_doklad(webdriver, app_url)
        statements.use_narrow_viewport(webdriver)

        statements.open_link_popover(webdriver)

        statements.assert_popover_not_clipped(webdriver)
