from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestManualEditorConflictReconcileAcceptance(AbstractFrontendTest):
    """Editor Extension E3.4 / H9.5: a stale autosave is reconciled, never a silent overwrite.

    Given the document was updated in another session
    When an autosave lands against a stale version
    Then it is rejected as a version conflict and reconciled
    And the other session's edit is not overwritten (last-writer-wins: the editor's edit wins)

    The jsdom conflict tests prove the refetch-and-retry protocol against a mocked 409. This
    drives a REAL 409: after the editor's first autosave settles on the server's version, a
    direct backend PUT (a stand-in second session) advances the server and staleness the editor's
    held version. Typing more fires an autosave at that stale version, the backend returns 409,
    and the app's saveDocument refetches and retries with the editor's content — observed live by
    the returning saved indicator (no error banner) and the persisted content read back through
    the backend.
    """

    def test_should_reconcile_a_stale_autosave_against_a_live_409(
        self, webdriver, app_url, manual_editor_conflict_reconcile_statements
    ):
        statements = manual_editor_conflict_reconcile_statements
        statements.open_manual_editor_for_doklad(webdriver, app_url)

        statements.type_text_in_editor(webdriver, "original")
        statements.assert_editor_autosaves_without_a_click(webdriver)

        statements.perform_out_of_band_edit(webdriver, "<p>other session</p>")

        statements.install_put_status_recorder(webdriver)
        statements.continue_typing_in_editor(webdriver, " more")
        statements.assert_autosave_reconciled_without_error(webdriver)
        statements.assert_stale_put_was_rejected_then_retried(webdriver)

        statements.assert_persisted_content_is(webdriver, "<p>original more</p>")
