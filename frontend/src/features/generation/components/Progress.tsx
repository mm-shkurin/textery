import type { ReactNode } from 'react'
import type { GenerationUiState } from '../hooks/useGeneration'
import { writingProgressMessage, type DocumentType } from '../../../shared/documentTypes'

interface ProgressProps {
  state: GenerationUiState
  documentType: DocumentType
}

export function Progress({ state, documentType }: ProgressProps) {
  return (
    <>
      <h3>Ход генерации</h3>
      <ChatMsg text="Анализирую тему и требования" />
      {state === 'pending' && (
        <ChatMsg active text={writingProgressMessage(documentType)}>
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
