import { describe, expect, it } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { AiChatPanel } from '../AiChatPanel'
import type { EditQuotaState } from '../../api/editQuotaApi'
import type { ChatMessage } from '../../api/chatMessagesApi'

// Story 19, Frontend Scenario 1.1 — the half its own Given structurally cannot reach.
//
// WHY THIS FILE EXISTS. Scenario 1.1 opens a document that has never been edited by AI, so every
// assertion it can write is satisfied by a message list that renders nothing under ANY condition
// and an `ai-chat-empty-state` that is unconditional. The acceptance test cannot tell those apart
// either — its document is pristine by construction. This case is the counter-case that makes the
// empty state CONDITIONAL, and it is why `AiChatPanel` takes its history as a prop: the panel is
// where the branch lives, so the panel is where it has to be observable.
//
// It renders the panel directly rather than through `DocumentEditorPage` on purpose. The page has
// no history read yet — scenario 1.2 owns it — so going through the page would mean asserting
// against a fetch this unit deliberately did not land.

const AI_CHAT_PANEL = 'ai-chat-panel'
const MESSAGE_LIST = 'ai-chat-message-list'
const EMPTY_STATE = 'ai-chat-empty-state'

// Prefix, matching the acceptance layer's `ANY_MESSAGE_INSIDE_THE_LIST`, and scoped inside the
// list: whatever scenario 1.2 names its rows, they answer to this, and the composer's own
// `ai-chat-message-input` stays outside the scope.
const ANY_MESSAGE = '[data-testid^="ai-chat-message"]'

const WITHIN_QUOTA: EditQuotaState = { exhausted: false, resetsAt: null }

// A user turn and an assistant turn, because a list that renders only one side would satisfy a
// single-message fixture while dropping half of every real conversation.
const HISTORY: ChatMessage[] = [
  { messageId: 'm-1', role: 'user', text: 'Сократи введение до одного абзаца' },
  { messageId: 'm-2', role: 'assistant', text: 'Готово — введение сокращено.' },
]
const EXPECTED_ROW_COUNT = 2

// RED: `AiChatPanel` has no history region at all — no `ai-chat-message-list`, no
// `ai-chat-empty-state`, and `messages` is an unread prop.
describe('AiChatPanel — a document that already has a conversation', () => {
  it('renders the messages and drops the empty state', () => {
    render(<AiChatPanel quota={WITHIN_QUOTA} messages={HISTORY} />)

    const panel = screen.getByTestId(AI_CHAT_PANEL)
    const list = within(panel).getByTestId(MESSAGE_LIST)

    // Absence, not "hidden": an empty state rendered invisibly still asserts that this document
    // has never been touched, which is false here. This is the assertion an unconditional empty
    // state fails, and the only reason the pristine scenario's own empty-state check means
    // anything.
    expect(within(panel).queryByTestId(EMPTY_STATE)).toBeNull()

    // Count AND content. Presence alone is satisfied by two blank rows, which is a history that
    // renders nothing while claiming a conversation happened.
    const rows = list.querySelectorAll(ANY_MESSAGE)
    // The literal, not `HISTORY.length`: an expected value derived from the fixture agrees with
    // itself under any edit to the fixture, which is the test computing what it should be asserting.
    expect(rows).toHaveLength(EXPECTED_ROW_COUNT)
    expect(rows[0].textContent).toContain(HISTORY[0].text)
    expect(rows[1].textContent).toContain(HISTORY[1].text)
  })
})
