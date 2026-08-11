"""Statements for UI scenario 1.2 — an existing conversation is restored on reopen.

Sign-in, the click-through into the editor route and the chat-panel element resolver come from
`editor_route_statements.py`; the navigation rationale lives there. The Given is issued by
`conversation_history_session.py`.

**What this scenario specifies that does not exist yet.** `AiChatPanel` can already RENDER a
transcript — 1.1's green built `AiChatHistory` with one `ai-chat-message` row per message — and
`chatMessagesApi.loadChatMessages` can already READ one. Nothing connects them:
`DocumentEditorPage.tsx:49` passes the literal `messages={[]}`, and `loadChatMessages` is
called by no production file (grep: its only non-test reference is its own definition). So a
reopened document shows the empty state no matter what its history holds. This scenario is what
forces the read to be issued and its result to reach the panel.

**And the second Then names a behavior that exists nowhere at all.** `.ac-chat-history` is
`overflow-y: auto`, and `scrollIntoView` / `scrollTop` appear ZERO times anywhere under
`frontend/src`. A restored conversation taller than the panel therefore opens scrolled to the
OLDEST message, with the newest below the fold — the exact opposite of what a chat should do.
"""

from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait

from statements.frontend.ai_chat.chat_history_viewport import (
    assert_the_history_itself_is_on_screen,
    assert_the_history_overflows,
    assert_the_row_is_fully_in_view,
    measure,
)
from statements.frontend.ai_chat.conversation_history_session import (
    issue_account_with_an_existing_conversation,
)
from statements.frontend.ai_chat.editor_route_statements import (
    EditorRouteStatements,
)
from statements.frontend.base_frontend_statements import WAIT_TIMEOUT_SECONDS

MESSAGE_LIST = (By.CSS_SELECTOR, "[data-testid='ai-chat-message-list']")
EMPTY_STATE = (By.CSS_SELECTOR, "[data-testid='ai-chat-empty-state']")

# Every row carries the SAME testid (`AiChatPanel.tsx:83` maps it over the messages), so this is
# resolved with `find_elements` and never `find_element` — the singular form would silently
# return the OLDEST row and make an ordering assertion unfalsifiable.
MESSAGE_ROW = (By.CSS_SELECTOR, "[data-testid='ai-chat-message']")

# The geometry this scenario's second Then turns on lives in `chat_history_viewport.py`.


class RestoredConversationStatements(EditorRouteStatements):
    """Carries the seeded transcript between the Given and the Thens.

    Instance state, unlike scenario 1.1's Statements which deliberately returns nothing: what
    the Thens compare against here is not a constant this layer owns but a runtime fact — the
    assistant's replies are model-generated. Threading it through the TEST class instead would
    put an implementation value in a file whose job is to narrate steps, and the fixture is
    function-scoped, so one instance serves exactly one test.
    """

    def __init__(self) -> None:
        super().__init__()
        self._expected_texts: tuple[str, ...] = ()

    def open_a_document_that_already_has_chat_messages(
        self, driver: WebDriver, app_url: str
    ) -> None:
        """Seed a real conversation, sign in, and CLICK the document open.

        A live session, not a seeded one: the editor route loads the document over the API on
        mount and a fake token 401s there, collapsing the client to the landing.

        "Reopens it" in the Gherkin is satisfied by this single open, not by an open-close-open
        cycle: the messages were written by HTTP calls outside the browser, so the browser has
        never held them in memory and this open is already a cold restore. A second visit would
        add a page load without adding a fact — and would risk passing on state the first visit
        left behind, which is the opposite of what "restored" is meant to prove.
        """
        account = issue_account_with_an_existing_conversation()
        self._expected_texts = account.transcript_texts
        self._sign_in_as(driver, app_url, account)
        self._open_the_only_document_by_clicking_it(driver, app_url, account)

    def assert_the_earlier_messages_are_shown_in_order(self, driver: WebDriver) -> None:
        """Rendered row texts equal the server's transcript, item for item, oldest first.

        Equality on the whole LIST rather than on membership: a panel that renders every message
        in reverse, or drops the middle turn, satisfies any per-row containment check while
        failing the only thing this Then asserts. The comparison therefore fixes both content
        and position in one statement.

        Whitespace is normalised on both sides. The row texts are model-generated prose in a
        `<p>`, where HTML collapses runs of whitespace and newlines before Selenium ever reads
        `.text`; comparing raw would make this scenario fail on the server having stored a line
        break, which is not what "shown in order" means anywhere.
        """
        rows = self._wait_for_the_whole_transcript_to_render(driver)
        actual = [self._normalised(row.text) for row in rows]
        expected = [self._normalised(text) for text in self._expected_texts]
        assert actual == expected, (
            f"expected the restored chat history to render the stored conversation oldest "
            f"first, {len(expected)} rows; got {len(actual)} rows: {actual} != {expected}"
        )

        # AFTER the positive anchor above, never before: the history arrives over an async read,
        # so an absence checked on first paint passes on every document, including one whose
        # history never loads at all. Ordering it behind a settled row count is what makes it
        # mean "the empty state is gone" instead of "the fetch has not landed yet".
        message_list = self._chat_panel_descendant(driver, MESSAGE_LIST, "message list")
        empty_states = message_list.find_elements(*EMPTY_STATE)
        assert not empty_states, (
            "expected NO chat empty state on a document that already has messages — the panel "
            f"is telling the user it has never been edited, found {len(empty_states)} element(s)"
        )

    def assert_the_newest_message_is_visible_without_scrolling(self, driver: WebDriver) -> None:
        """The newest row's box lies inside the history's visible box, on a history that scrolls.

        Measured, never `is_displayed()` — Selenium calls a row scrolled out of an
        `overflow-y: auto` container displayed, so that check would pass on the very layout this
        Then exists to reject. `chat_history_viewport.py` holds the rects and the reasoning.
        """
        rows = self._wait_for_the_whole_transcript_to_render(driver)
        message_list = self._chat_panel_descendant(driver, MESSAGE_LIST, "message list")
        # `rows[-1]` is the NEWEST because the list is oldest-first: the server fixes that order
        # (documents_messages_list.yaml), the setup asserts it on `created_at`, and the Then
        # above has already proved the rendered rows match that order item for item.
        box = measure(driver, message_list, rows[-1])
        assert_the_history_overflows(box)
        assert_the_history_itself_is_on_screen(box)
        assert_the_row_is_fully_in_view(box, "the newest message")

    def _wait_for_the_whole_transcript_to_render(self, driver: WebDriver) -> list[WebElement]:
        """Poll the list until it holds exactly as many rows as the server stored.

        Synchronisation, not convenience: the history is fetched after mount, so both Thens
        would otherwise read a list that is empty or half-filled and fail with a count instead
        of with the fact they exist to check.

        Re-resolves the list on every poll and tolerates staleness for the reason
        `_chat_panel_descendant` documents — the panel re-renders under the test's feet when the
        quota read and the history read settle at different moments.

        The Given-ran guard lives HERE, not in one Then, because both Thens enter through this
        method. Without it a missing Given makes `expected_count` zero, and a zero-row wait would
        burn the full timeout and then report "render all 0 stored messages" — a message that
        accuses the panel of the test's own setup gap.
        """
        assert self._expected_texts, (
            "the Given must run before this Then — no seeded transcript is held, so there is "
            "nothing to compare the rendered rows against"
        )
        expected_count = len(self._expected_texts)
        return WebDriverWait(
            driver,
            WAIT_TIMEOUT_SECONDS,
            ignored_exceptions=(StaleElementReferenceException,),
        ).until(
            lambda d: self._rows_when_all_present(d, expected_count),
            f"expected the chat history to render all {expected_count} stored messages",
        )

    def _rows_when_all_present(
        self, driver: WebDriver, expected_count: int
    ) -> list[WebElement] | None:
        message_list = self._chat_panel_descendant(driver, MESSAGE_LIST, "message list")
        rows = [row for row in message_list.find_elements(*MESSAGE_ROW) if row.is_displayed()]
        return rows if len(rows) == expected_count else None

    @staticmethod
    def _normalised(text: str) -> str:
        return " ".join(text.split())
