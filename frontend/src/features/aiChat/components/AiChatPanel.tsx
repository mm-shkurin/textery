import type { EditQuotaState } from '../api/editQuotaApi'
import { AiChatComposer } from './AiChatComposer'
import { AiChatRevisions } from './AiChatRevisions'
import './AiChatPanel.css'

export const CHAT_PANEL_HEADING = 'Редактор с ИИ'
// Shown only while the account's quota is still unknown. It is not a placeholder for the
// composer: it is what the panel can honestly say before it knows whether typing is allowed.
export const CHAT_PANEL_NOTICE = 'Проверяем дневной лимит правок…'

// One turn of the conversation. RED stub for Frontend Scenario 1.1: only the three fields the
// tests read — an id to key the row, the side it sits on, and what it says. The wire shape and
// its timestamps belong to `red-frontend-api` / scenario 1.2, which owns the history read.
export interface ChatMessage {
  messageId: string
  role: 'user' | 'assistant'
  text: string
}

interface AiChatPanelProps {
  // `null` = not yet known. The composer is WITHHELD until the quota resolves rather than
  // rendered live and disabled a tick later — an enabled send control the user may click before
  // the read lands is a promise the account cannot keep.
  quota: EditQuotaState | null
  // The conversation so far. Deliberately a PROP and not a read of its own: the panel is what
  // scenario 1.1's empty state and scenario 1.2's restored history disagree about, so the panel
  // is where the branch has to be testable. Unread by the body below — RED plumbing, so the
  // tests compile and fail on the missing history region rather than on a type error.
  messages: ChatMessage[]
}

// The mockup's accent tile beside the heading (`.chat-head .mark`). There is no icon package
// in this app — every other screen inlines its glyph — and it is decoration, so it is hidden
// from assistive tech rather than given a label the heading already carries.
function SparkMark() {
  return (
    <span className="ac-chat-mark" aria-hidden="true">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z" />
      </svg>
    </span>
  )
}

export function AiChatPanel({ quota }: AiChatPanelProps) {
  return (
    <aside className="ac-chat" aria-label={CHAT_PANEL_HEADING} data-testid="ai-chat-panel">
      <div className="ac-chat-head">
        <SparkMark />
        <h2 className="ac-chat-heading">{CHAT_PANEL_HEADING}</h2>
        <AiChatRevisions />
      </div>
      {quota === null ? (
        <p className="ac-chat-notice">{CHAT_PANEL_NOTICE}</p>
      ) : (
        <AiChatComposer quota={quota} />
      )}
    </aside>
  )
}
