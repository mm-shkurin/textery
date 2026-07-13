import { useState } from 'react'
import './ChatWorkspace.css'
import './ChatWorkspaceDoc.css'
import type { GenerationUiState } from '../hooks/useGeneration'
import { Composer, MAX_TOPIC_LENGTH } from './Composer'
import { Progress } from './Progress'
import { DocArea } from './DocArea'

interface ChatWorkspaceProps {
  documentTypeLabel: string
  state: GenerationUiState
  content: string | null
  volumePages: number | null
  createdAt?: string | null
  error: string | null
  onSubmit: (topic: string) => void
  onReset: () => void
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
  const [topic, setTopic] = useState('')

  const send = () => {
    const trimmed = topic.trim().slice(0, MAX_TOPIC_LENGTH)
    if (trimmed) onSubmit(trimmed)
  }

  return (
    <div className="chat-page">
      <header className="cw-header">
        <img className="cw-logo" src="/logo.svg" alt="Textery" />
      </header>
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
