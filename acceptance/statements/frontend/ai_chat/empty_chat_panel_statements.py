"""Statements for UI scenario 1.1 — editor and chat panel side by side, history empty.

Sign-in, the click-through into the editor route and the chat-panel element resolver come
from `editor_route_statements.py`; the navigation rationale lives there. The Given is issued
by `pristine_document_session.py`.

**What this scenario specifies that does not exist yet.** The panel today renders a heading,
a revisions control and — while the quota read is unresolved — a notice. It has NO history
region at all: no message list, no empty state. Both are named here for the first time, and
the enabled composer is named for the first time in the POSITIVE (scenario 0.2 asserts only
that it can be dead).
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from statements.frontend.ai_chat.editor_route_statements import (
    MESSAGE_INPUT,
    SEND_BUTTON,
    EditorRouteStatements,
)
from statements.frontend.ai_chat.pristine_document_session import (
    DOCUMENT_PARAGRAPH_TEXT,
    issue_account_with_a_document_never_edited_by_ai,
)

# `manual-editor` is NOT unique to this route: story 5's `ManualEditor` carries the same testid
# (`frontend/src/features/generation/components/ManualEditor.tsx:158`) as well as story 19's
# `EditorDocumentView`. Only one of them renders on `/documents/:id` today, and the count below
# is what keeps that true — with both mounted a document-scoped text check would silently read
# whichever came first in the DOM.
MANUAL_EDITOR = (By.CSS_SELECTOR, "[data-testid='manual-editor']")
EXPECTED_MANUAL_EDITOR_COUNT = 1

MESSAGE_LIST = (By.CSS_SELECTOR, "[data-testid='ai-chat-message-list']")
EMPTY_STATE = (By.CSS_SELECTOR, "[data-testid='ai-chat-empty-state']")

# Prefix, and scoped to the message list, for the reason scenario 0.1's absence check
# established: an exact testid that exists nowhere makes an absence check vacuous forever —
# it keeps passing whatever a later scenario names its message rows. Matching the whole
# `ai-chat-message*` namespace INSIDE the list means no naming choice in scenario 1.2 (which
# renders the first real rows) can slip past this. Scoping to the list is what keeps the
# composer's own `ai-chat-message-input` from matching.
ANY_MESSAGE_INSIDE_THE_LIST = (By.CSS_SELECTOR, "[data-testid^='ai-chat-message']")

# The sentence `mockups/desktop/01-editor-chat.html` puts in the panel's first bubble. It is
# the empty state in everything but placement: it is what the assistant says to a document it
# has not touched. This test moves it out of the message list and into an element of its own,
# because a greeting rendered as a MESSAGE is a message the server never sent — and scenario
# 1.2, which asserts the restored history renders in order, would then have to reason about a
# row that is not part of any history.
EXPECTED_EMPTY_STATE_TEXT = (
    "Документ готов. Напишите, что нужно изменить — я поправлю текст и сохраню новую версию."
)


class EmptyChatPanelStatements(EditorRouteStatements):
    def open_a_document_never_edited_by_ai(self, driver: WebDriver, app_url: str) -> None:
        """Prepare the account's one document, sign in, and CLICK it open.

        A live session, not a seeded one: the editor route loads the document over the API on
        mount and a fake token 401s there, collapsing the client to the landing.

        Returns nothing on purpose: everything the Thens compare against is a constant this
        layer owns, so there is no runtime value for the test class to carry between steps.
        """
        account = issue_account_with_a_document_never_edited_by_ai()
        self._sign_in_as(driver, app_url, account)
        self._open_the_only_document_by_clicking_it(driver, app_url, account)

    def assert_the_document_content_is_shown_in_the_editor(self, driver: WebDriver) -> None:
        """Equality on the rendered TEXT, not a substring and not mere presence.

        The editor is the route's other half — "side by side" is only half true if the chat
        panel arrives beside an empty page — and the stored content is a paragraph the setup
        wrote and re-read over the same endpoint the route reads, so the expected value is the
        one the setup stored rather than anything taken off the screen.

        `DOCUMENT_PARAGRAPH_TEXT` is read from the setup module rather than threaded through
        the test class: it is a fixed constant this layer owns, and a test class that carries
        it is holding an implementation value instead of narrating a step.
        """
        self._wait_for_visible(driver, MANUAL_EDITOR)
        editors = driver.find_elements(*MANUAL_EDITOR)
        assert len(editors) == EXPECTED_MANUAL_EDITOR_COUNT, (
            f"expected exactly {EXPECTED_MANUAL_EDITOR_COUNT} 'manual-editor' element on the "
            f"editor route (the testid is shared with story 5's editor), found {len(editors)}"
        )
        self._assert_element_text_equals(
            driver, MANUAL_EDITOR, DOCUMENT_PARAGRAPH_TEXT, "editor document content"
        )

    def assert_the_chat_panel_shows_its_empty_state(self, driver: WebDriver) -> None:
        """The panel is present, its history region is present, and it holds NO messages.

        The list is asserted alongside the empty state rather than instead of it: an empty
        state shown while no history region exists at all would satisfy "empty" by having
        nowhere to put messages, and scenario 1.2 would then be building the region from
        scratch on a panel this scenario called done.
        """
        message_list = self._chat_panel_descendant(driver, MESSAGE_LIST, "message list")
        assert message_list.is_displayed(), "expected the chat message list to be displayed"

        messages = message_list.find_elements(*ANY_MESSAGE_INSIDE_THE_LIST)
        assert not messages, (
            "expected no messages in the chat history of a document never edited by AI, "
            f"found {len(messages)} element(s) in the message list"
        )

        empty_state = self._chat_panel_descendant(driver, EMPTY_STATE, "chat empty state")
        assert empty_state.is_displayed(), "expected the chat empty state to be displayed"

        actual_text = empty_state.text.strip()
        assert actual_text == EXPECTED_EMPTY_STATE_TEXT, (
            f"expected the chat empty state to read '{EXPECTED_EMPTY_STATE_TEXT}', "
            f"got '{actual_text}'"
        )

    def assert_the_message_input_is_enabled(self, driver: WebDriver) -> None:
        """Both halves of "the message input is enabled", and the mirror of scenario 0.2.

        The send control is asserted beside the input because a live input above a dead send
        control lets the user type an instruction they can never submit — which is the Then
        satisfied on screen and not in fact.

        Displayed is asserted beside enabled for the same reason in the other direction:
        `is_enabled()` is `True` for an input that is `display:none`, zero-height, or stacked
        behind the quota notice, so enabled alone would pass a composer the user cannot reach.
        """
        message_input = self._chat_panel_descendant(driver, MESSAGE_INPUT, "message input")
        assert message_input.is_displayed(), "expected the chat message input to be displayed"
        assert message_input.is_enabled(), "expected the chat message input to be enabled"

        send_button = self._chat_panel_descendant(driver, SEND_BUTTON, "send control")
        assert send_button.is_displayed(), "expected the chat send control to be displayed"
        assert send_button.is_enabled(), "expected the chat send control to be enabled"
