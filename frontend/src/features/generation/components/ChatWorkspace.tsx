import { useState } from 'react'
import './ChatWorkspace.css'
import './ChatWorkspaceDoc.css'
import type { GenerationUiState } from '../hooks/useGeneration'
import { Composer, MAX_TOPIC_LENGTH } from './Composer'
import { Progress } from './Progress'
import { DocArea } from './DocArea'
import { AppHeader } from '../../../shared/components/AppHeader'

interface ChatWorkspaceProps {
  documentTypeLabel: string
  state: GenerationUiState
  content: string | null
  volumePages: number | null
  createdAt?: string | null
  error: string | null
  onSubmit: (topic: string) => void
  onReset: () => void
  // The workspace is where a signed-in user actually spends their time, and it replaces the
  // landing entirely — so without a sign-out here, the only way out of a session on a shared
  // machine is closing the tab.
  onLogoutClick?: () => void
}

const BADGE: Record<GenerationUiState, string> = {
  idle: 'Новый запрос',
  pending: 'В обработке',
  completed: 'Готово',
  failed: 'Ошибка',
}

export function ChatWorkspace(props: ChatWorkspaceProps) {
  const { documentTypeLabel, state, content, volumePages, createdAt, error, onSubmit, onReset } =
    props
  const { onLogoutClick } = props
  const [topic, setTopic] = useState('')

  const send = () => {
    const trimmed = topic.trim().slice(0, MAX_TOPIC_LENGTH)
    if (trimmed) onSubmit(trimmed)
  }

  return (
    <div className="chat-page">
      <AppHeader onLogoutClick={onLogoutClick} />
      <div className="cw-container">
        <div className={`cw-badge cw-badge-${state}`}>
          <span className="cw-dot" />
          {BADGE[state]}
        </div>
        <div className="cw-layout">
          <aside className="chat-panel" data-testid="chat-panel">
            {state === 'idle' ? (
              <Composer topic={topic} setTopic={setTopic} onSend={send} />
            ) : (
              <Progress state={state} />
            )}
          </aside>
          <section className="doc-area" data-testid="doc-area">
            <DocArea
              state={state}
              content={content}
              volumePages={volumePages}
              createdAt={createdAt ?? null}
              error={error}
              label={documentTypeLabel}
              onReset={onReset}
            />
          </section>
        </div>
      </div>
    </div>
  )
}
