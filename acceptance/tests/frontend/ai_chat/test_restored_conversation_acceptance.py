import pytest

from tests.frontend.abstract_frontend_test import AbstractFrontendTest

# RED (2026-08-11). The stack could not be run to observe the failure — the Docker daemon is
# down on this host — and a run would have produced ERR_CONNECTION_REFUSED, an environment fact
# and not this scenario's red. The RED evidence is collection + import resolution + the
# prediction below, on the precedent scenarios 0.1 and 1.1 set.
#
# THE SKIP REASON HERE IS NOT 1.1's. Scenario 1.1's setup was fully supported (`POST /documents`
# + `PUT /documents/{id}`, both registered) and 0.2's was blocked by the unregistered quota
# READ. This one is blocked at the WRITE: "a document with earlier chat messages" can only be
# reached through `POST /documents/{id}/ai-edits`, because `endpoints.md` lists no endpoint that
# writes a message — messages are a side effect of an edit. `main.py:115-118` registers exactly
# four routers (generation, auth, oauth, document); `document_edit_router` is not among them, so
# that POST answers 404 and there is no other way to create a message.
#
# So against a live stack today the FIRST failure is in the Given, not in a Then:
#
#   AssertionError — "restored-conversation setup: queueing the edit 'Перепиши введение...'
#   expected 202, got 404: ..." — from `_assert_status` in `conversation_history_session.py`,
#   raised through `open_a_document_that_already_has_chat_messages`.
#
# Once that router is registered, the failures the scenario actually exists to force are, in
# the order the test meets them:
#   1. FIRST Then. `DocumentEditorPage.tsx:49` passes the literal `messages={[]}` to
#      `AiChatPanel`, and `loadChatMessages` (`chatMessagesApi.ts:111`) is called by no
#      production file — grep finds its only non-test reference is its own definition. The
#      panel can render rows and the client can fetch them; nothing joins the two. So the
#      restored history renders zero rows and the empty state stays up:
#      TimeoutException — "expected the chat history to render all N stored messages".
#   2. SECOND Then. `scrollIntoView` and `scrollTop` appear ZERO times anywhere under
#      `frontend/src`, while `.ac-chat-history` is `overflow-y: auto`. A conversation taller
#      than the panel therefore opens pinned to the OLDEST message:
#      AssertionError — "the newest message ends below the visible bottom of the chat history".
# Un-skip at green-selenium, which per tdd-rules.md is remove-marker-only.
@pytest.mark.skip(
    reason="RED: no chat history read is wired into the editor page, and the history never "
    "scrolls to the newest message; the Given also needs POST /ai-edits, whose router is "
    "unregistered in main.py"
)
class TestRestoredConversationAcceptance(AbstractFrontendTest):
    """UI Test Scenario 1.2: An existing conversation is restored when the document is reopened.

    Given a document with earlier chat messages
    When the user reopens it
    Then the earlier messages are shown in order
    And the newest message is visible without scrolling
    """

    def test_should_restore_the_conversation_in_order_with_the_newest_message_in_view(
        self, webdriver, app_url, restored_conversation_statements
    ):
        restored_conversation_statements.open_a_document_that_already_has_chat_messages(
            webdriver, app_url
        )

        restored_conversation_statements.assert_the_earlier_messages_are_shown_in_order(webdriver)
        restored_conversation_statements.assert_the_newest_message_is_visible_without_scrolling(
            webdriver
        )
