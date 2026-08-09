export const CHAT_PANEL_HEADING = 'Редактор с ИИ'
// Deliberately NOT the mockup's "Напишите, что нужно изменить" opener: there is no composer on
// this route yet (scenario 1.1 owns the message list, the composer and the quota line), and an
// invitation to type into an input that does not exist is a lie told by a placeholder. This says
// what is true today and nothing more.
export const CHAT_PANEL_NOTICE = 'Редактирование через чат появится здесь.'

export function AiChatPanel() {
  return (
    <aside className="ac-chat" aria-label={CHAT_PANEL_HEADING} data-testid="ai-chat-panel">
      <h2 className="ac-chat-heading">{CHAT_PANEL_HEADING}</h2>
      <p className="ac-chat-notice">{CHAT_PANEL_NOTICE}</p>
    </aside>
  )
}
