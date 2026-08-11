import type { EditQuotaState } from '../api/editQuotaApi'
// The conversation's row type, owned by the api layer that produces it. Rationale beside the
// declaration; the panel is a consumer of the shape, not its author.
import type { ChatMessage } from '../api/chatMessagesApi'
import { AiChatComposer } from './AiChatComposer'
import { AiChatRevisions } from './AiChatRevisions'
import './AiChatPanel.css'

export const CHAT_PANEL_HEADING = 'Редактор с ИИ'
// Shown only while the account's quota is still unknown. It is not a placeholder for the
// composer: it is what the panel can honestly say before it knows whether typing is allowed.
export const CHAT_PANEL_NOTICE = 'Проверяем дневной лимит правок…'
// Shown only while the conversation is empty. Exported so the vitest layer can import the one
// copy instead of retyping it — the acceptance layer (`empty_chat_panel_statements.py`) is a
// separate language and cannot share it, so two copies is the floor, three was avoidable.
export const CHAT_EMPTY_STATE_TEXT =
  'Документ готов. Напишите, что нужно изменить — я поправлю текст и сохраню новую версию.'

interface AiChatPanelProps {
  // `null` = not yet known. The composer is WITHHELD until the quota resolves rather than
  // rendered live and disabled a tick later — an enabled send control the user may click before
  // the read lands is a promise the account cannot keep.
  quota: EditQuotaState | null
  // The conversation so far. Deliberately a PROP and not a read of its own: the panel is what
  // scenario 1.1's empty state and scenario 1.2's restored history disagree about, so the panel
  // is where the branch has to be testable.
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

// The history region's accessible name. Not exported: no assertion reads it, and both test layers
// locate the region by `data-testid`.
const CHAT_HISTORY_LABEL = 'История переписки с ИИ'

// The history region. The list is rendered unconditionally — it is where messages go, and a
// region that appears only once a message exists would have to be built twice. The empty state
// is the conditional half: it claims "this document has never been edited", which is false the
// moment a single turn exists.
//
// Rows carry `text` and nothing else. Keying by id, splitting user from assistant and ordering
// the turns are scenario 1.2's, which owns the history read.
//
// `role="log"` + `aria-live="polite"` because this is the app's most frequently-updating region
// and a reply that arrives silently is a reply a screen-reader user never hears — they retype the
// instruction and burn a quota unit. It follows the `aria-live` half of the convention
// `AuthLoadingIndicator.tsx` sets, and DEPARTS from the other half: that file argues for `<output>`
// over `role="status"` on a div, on the grounds that an element carrying the role implicitly states
// its semantics instead of annotating them. No HTML element carries `role="log"` implicitly, so
// annotating is forced here — `log` rather than `output` because the semantic is an appended
// transcript, not one computed result. Attributes only, and every locator in both test layers is a
// `data-testid`, which is why no assertion moved.
//
// WARNING FOR SCENARIO 1.2: this announces on insert, which is right for one arriving reply and
// wrong for the restore path 1.2 owns — a whole transcript injected after mount would be read out
// in full. 1.2 must suppress announcement during initial hydration.
function AiChatHistory({ messages }: { messages: ChatMessage[] }) {
  return (
    <div
      className="ac-chat-history"
      role="log"
      aria-live="polite"
      aria-label={CHAT_HISTORY_LABEL}
      data-testid="ai-chat-message-list"
    >
      {messages.length === 0 ? (
        <p className="ac-chat-empty" data-testid="ai-chat-empty-state">
          {CHAT_EMPTY_STATE_TEXT}
        </p>
      ) : (
        messages.map((message) => (
          <p className="ac-chat-message" key={message.messageId} data-testid="ai-chat-message">
            {message.text}
          </p>
        ))
      )}
    </div>
  )
}

export function AiChatPanel({ quota, messages }: AiChatPanelProps) {
  return (
    <aside className="ac-chat" aria-label={CHAT_PANEL_HEADING} data-testid="ai-chat-panel">
      <div className="ac-chat-head">
        <SparkMark />
        <h2 className="ac-chat-heading">{CHAT_PANEL_HEADING}</h2>
        <AiChatRevisions />
      </div>
      <AiChatHistory messages={messages} />
      {quota === null ? (
        <p className="ac-chat-notice">{CHAT_PANEL_NOTICE}</p>
      ) : (
        <AiChatComposer quota={quota} />
      )}
    </aside>
  )
}
