import { useState } from 'react'
import type { ReactNode } from 'react'
import './ChatWorkspace.css'
import './ChatWorkspaceDoc.css'
import type { GenerationUiState } from '../hooks/useGeneration'

interface ChatWorkspaceProps {
  documentTypeLabel: string
  state: GenerationUiState
  content: string | null
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
  const { documentTypeLabel, state, content, error, onSubmit, onReset } = props
  const [topic, setTopic] = useState('')

  const send = () => {
    const trimmed = topic.trim()
    if (trimmed) onSubmit(trimmed)
  }

  return (
    <div className="chat-page">
      <header className="cw-header">
        <div className="cw-logo">
          <span className="cw-logo-mark">T</span>Textery
        </div>
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

interface ComposerProps {
  topic: string
  setTopic: (v: string) => void
  onSend: () => void
}

function Composer({ topic, setTopic, onSend }: ComposerProps) {
  return (
    <div className="composer">
      <h3>Тема доклада</h3>
      <textarea
        className="composer-input"
        data-testid="topic-input"
        placeholder="Например: Влияние искусственного интеллекта на образование"
        value={topic}
        onChange={(e) => setTopic(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) onSend()
        }}
        rows={4}
      />
      <button
        type="button"
        className="cw-btn cw-btn-primary composer-send"
        data-testid="topic-send"
        onClick={onSend}
        disabled={!topic.trim()}
      >
        Сгенерировать
      </button>
    </div>
  )
}

function Progress({ state }: { state: GenerationUiState }) {
  return (
    <>
      <h3>Ход генерации</h3>
      <ChatMsg text="Анализирую тему и требования" />
      {state === 'pending' && (
        <ChatMsg active text="ИИ пишет доклад">
          <span className="typing-dots">
            <span />
            <span />
            <span />
          </span>
        </ChatMsg>
      )}
      {state === 'completed' && (
        <>
          <ChatMsg text="Пишу доклад" />
          <ChatMsg done text="Готово!" />
        </>
      )}
      {state === 'failed' && <ChatMsg error text="Не удалось завершить" />}
    </>
  )
}

interface ChatMsgProps {
  text: string
  active?: boolean
  done?: boolean
  error?: boolean
  children?: ReactNode
}

function ChatMsg({ text, active, done, error, children }: ChatMsgProps) {
  const bubbleCls = ['chat-bubble', active && 'active', done && 'done', error && 'error']
    .filter(Boolean)
    .join(' ')
  return (
    <div className="chat-msg">
      <div className={`chat-avatar${error ? ' error-avatar' : ''}`}>{error ? '✕' : '✦'}</div>
      <div className={bubbleCls}>
        {text}
        {children}
      </div>
    </div>
  )
}

interface DocAreaProps {
  state: GenerationUiState
  content: string | null
  error: string | null
  label: string
  onReset: () => void
}

function DocArea({ state, content, error, label, onReset }: DocAreaProps) {
  if (state === 'completed') {
    return (
      <div className="doc-content">
        <div className="doc-meta">{label} · 5 страниц · создан только что</div>
        <div className="doc-body" data-testid="doc-body">
          {content}
        </div>
        <div className="actions-row">
          <button type="button" className="cw-btn cw-btn-primary" onClick={onReset}>
            Создать новый доклад
          </button>
        </div>
      </div>
    )
  }
  if (state === 'failed') {
    return (
      <div className="doc-placeholder" data-testid="doc-error">
        <div className="icon-circle">✕</div>
        <h2>Не удалось сгенерировать доклад</h2>
        <p>{error ?? 'Попробуйте создать новый запрос — измените тему или требования.'}</p>
        <button type="button" className="cw-btn cw-btn-primary" onClick={onReset}>
          Создать новый запрос
        </button>
      </div>
    )
  }
  if (state === 'pending') {
    return (
      <div className="doc-placeholder">
        <div className="spinner" />
        <h2>Готовим ваш доклад</h2>
        <p>Обычно занимает 1–2 минуты — страница обновится автоматически</p>
      </div>
    )
  }
  return (
    <div className="doc-placeholder">
      <h2>Опишите тему доклада</h2>
      <p>Введите тему в панели слева — ИИ сгенерирует готовый текст.</p>
    </div>
  )
}
