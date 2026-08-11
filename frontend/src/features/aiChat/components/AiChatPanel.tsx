import type { EditQuotaState } from '../api/editQuotaApi'
import { AiChatComposer } from './AiChatComposer'
import { AiChatRevisions } from './AiChatRevisions'
import './AiChatPanel.css'

export const CHAT_PANEL_HEADING = 'Редактор с ИИ'
// Shown only while the account's quota is still unknown. It is not a placeholder for the
// composer: it is what the panel can honestly say before it knows whether typing is allowed.
export const CHAT_PANEL_NOTICE = 'Проверяем дневной лимит правок…'

interface AiChatPanelProps {
  // `null` = not yet known. The composer is WITHHELD until the quota resolves rather than
  // rendered live and disabled a tick later — an enabled send control the user may click before
  // the read lands is a promise the account cannot keep.
  quota: EditQuotaState | null
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
