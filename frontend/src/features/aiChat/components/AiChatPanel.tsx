export const CHAT_PANEL_HEADING = 'Редактор с ИИ'
// Deliberately NOT the mockup's "Напишите, что нужно изменить" opener: there is no composer on
// this route yet (scenario 1.1 owns the message list, the composer and the quota line), and an
// invitation to type into an input that does not exist is a lie told by a placeholder. This says
// what is true today and nothing more.
export const CHAT_PANEL_NOTICE = 'Редактирование через чат появится здесь.'

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

export function AiChatPanel() {
  return (
    <aside className="ac-chat" aria-label={CHAT_PANEL_HEADING} data-testid="ai-chat-panel">
      <div className="ac-chat-head">
        <SparkMark />
        <h2 className="ac-chat-heading">{CHAT_PANEL_HEADING}</h2>
      </div>
      <p className="ac-chat-notice">{CHAT_PANEL_NOTICE}</p>
    </aside>
  )
}
