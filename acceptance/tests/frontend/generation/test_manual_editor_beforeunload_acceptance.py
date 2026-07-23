from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestManualEditorBeforeUnloadGuardAcceptance(AbstractFrontendTest):
    """Track B owe (guard-unsaved-work): the beforeunload guard arms/disarms live.

    Given a freshly created (dirty) manual document
    Then a real-window beforeunload is cancelled (the guard is armed)
    And once a save leaves the document clean, a beforeunload passes through (the guard is removed)

    This proves — in a real browser, through Chrome's own event system — that the guard's
    useEffect binds a window beforeunload listener while dirty and its cleanup removes it once
    clean. The VISIBLE native dialog and the string returnValue are NOT assertable in headless
    (see the statements module: headless auto-handles the dialog, and a synthetic event exposes
    only the legacy boolean returnValue in every engine); those stay runtime behavior.
    """

    def test_should_arm_the_guard_while_dirty_and_remove_it_once_saved_clean(
        self, webdriver, app_url, manual_editor_beforeunload_statements
    ):
        statements = manual_editor_beforeunload_statements
        statements.open_manual_editor_for_doklad(webdriver, app_url)

        # A freshly created document is dirty (not yet saved) — the guard must be armed.
        statements.assert_beforeunload_guard_is_armed(webdriver)

        statements.save_until_clean(webdriver)

        # Saved clean — the effect cleanup must have removed the listener.
        statements.assert_beforeunload_guard_is_disarmed(webdriver)
