import pytest

from tests.frontend.abstract_frontend_test import AbstractFrontendTest

# RED (2026-08-11). The stack could not be run to observe the failure — the Docker daemon is
# down on this host, so neither backend nor frontend is reachable — and a run would have
# produced ERR_CONNECTION_REFUSED, which is an environment fact and not this scenario's red.
# The RED evidence is therefore collection + import resolution + the prediction below, on the
# precedent scenario 0.1's red-selenium set. UNLIKE scenario 0.2, this test's SETUP is fully
# supported today: it uses only story 5's `POST /documents` and `PUT /documents/{id}`, both
# registered in `main.py`. So against a live stack the failure would be an application one:
#
#   TimeoutException — "expected a visible message list inside the chat panel, found none" —
#   from `_chat_panel_descendant`'s panel-scoped wait on `[data-testid='ai-chat-message-list']`,
#   raised through `assert_the_chat_panel_shows_its_empty_state`, the SECOND Then.
#
# The first Then passes: `EditorDocumentView` renders the stored content. Two things are
# missing, in the order the test meets them:
#   1. The chat panel has no history region at all — neither `ai-chat-message-list` nor
#      `ai-chat-empty-state` appears anywhere under `frontend/src` (verified by grep).
#      `AiChatPanel` renders a heading, the revisions control, and then either the composer
#      or a notice. This scenario names both elements for the first time.
#   2. The message input would fail the THIRD Then even once the list exists:
#      `AiChatPanel` withholds `AiChatComposer` until the quota resolves, and
#      `loadEditQuota` reads `GET /api/v1/ai-edits/quota`, which is not a registered route —
#      the read fails, `useEditQuota` stays `null`, and no input is rendered to be enabled.
# Un-skip at green-selenium, which per tdd-rules.md is remove-marker-only.
@pytest.mark.skip(reason="RED: no chat history region; composer withheld, quota route unregistered")
class TestEmptyChatPanelAcceptance(AbstractFrontendTest):
    """UI Test Scenario 1.1: The editor and chat panel render side by side with an empty
    history.

    Given the user opens a document that has never been edited by AI
    Then the document content is shown in the editor
    And the chat panel is shown with its empty state
    And the message input is enabled
    """

    def test_should_show_the_document_beside_an_empty_chat_with_a_live_input(
        self, webdriver, app_url, empty_chat_panel_statements
    ):
        empty_chat_panel_statements.open_a_document_never_edited_by_ai(webdriver, app_url)

        empty_chat_panel_statements.assert_the_document_content_is_shown_in_the_editor(webdriver)
        empty_chat_panel_statements.assert_the_chat_panel_shows_its_empty_state(webdriver)
        empty_chat_panel_statements.assert_the_message_input_is_enabled(webdriver)
