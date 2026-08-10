import pytest

from tests.frontend.abstract_frontend_test import AbstractFrontendTest

# RED (2026-08-10). Confirmed failing before this marker went on, and the failure is in the
# SETUP, one layer before anything this scenario asserts:
#   AssertionError: over-quota setup: probe 0 expected 202 or 429, got 404: {"detail":"Not Found"}
# Three things are absent, in the order the test meets them:
#   1. `POST /api/v1/documents/{id}/ai-edits` is not a registered route at all —
#      `backend/adapters/rest/src/router/document_edit/document_edit_router.py` exists but no
#      composition root includes it, and its seven usecase providers still raise
#      NotImplementedError. So the quota counter cannot be moved and the Given is unreachable.
#   2. No endpoint reports quota state on document open (the contract gap in the class
#      docstring) — even a spent quota would reach no screen.
#   3. The chat composer, the reset hint and the revisions panel do not exist; scenario 1.1
#      builds the first, this scenario names the other two.
# Un-skip at green-selenium, which per tdd-rules.md is remove-marker-only: if it does not pass
# then, the missing work belongs to an earlier phase, not to this file.
@pytest.mark.skip(reason="RED: AI-edit routes unregistered, no quota read, no chat composer")
class TestOverQuotaEditorAcceptance(AbstractFrontendTest):
    """UI Test Scenario 0.2: An account over its daily quota cannot type an instruction.

    Given the user's account has reached its daily edit quota
    When they open a document
    Then the chat input is disabled
    And the reset hint is shown
    And the revisions panel remains usable

    **This test specifies a contract addition green must make.** No endpoint reports quota
    state on document open — `resets_at` lives only in the `429` body of `POST /ai-edits`
    (`documents_ai_edits_create.yaml:104`) and `endpoints.md`'s seven endpoints carry no
    quota fields — so the Then above has no data source today. Green owes a quota-state
    read the editor route issues on open. The gap, and why the Gherkin was not rewritten
    around a post-429 disable instead, are argued in `over_quota_session.py`'s docstring.
    """

    def test_should_disable_the_chat_input_and_show_the_reset_hint(
        self, webdriver, app_url, over_quota_statements
    ):
        account = over_quota_statements.open_a_document_of_an_account_over_its_quota(
            webdriver, app_url
        )

        over_quota_statements.assert_the_chat_input_is_disabled(webdriver)
        over_quota_statements.assert_the_reset_hint_is_shown(webdriver, account.resets_at)

        over_quota_statements.open_the_revisions_panel(webdriver)
        over_quota_statements.assert_the_revisions_panel_lists_the_history(webdriver)
