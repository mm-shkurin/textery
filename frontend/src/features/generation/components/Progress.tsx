import type { ReactNode } from 'react'
import type { GenerationUiState } from '../hooks/useGeneration'
import { type DocumentType } from '../../../shared/domain/documentTypes'
import {
  writingProgressMessage,
  writtenProgressMessage,
} from '../../../shared/copy/documentTypeCopy'
import chatWorkspaceStyles from './ChatWorkspace.module.css'

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
          <span className={chatWorkspaceStyles['typing-dots']}>
            <span />
            <span />
            <span />
          </span>
        </ChatMsg>
      )}
      {state === 'completed' && (
        <>
          <ChatMsg text={writtenProgressMessage(documentType)} />
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
  const bubbleCls = [
    chatWorkspaceStyles['chat-bubble'],
    active && chatWorkspaceStyles.active,
    done && chatWorkspaceStyles.done,
    error && chatWorkspaceStyles.error,
  ]
    .filter(Boolean)
    .join(' ')
  return (
    <div className={chatWorkspaceStyles['chat-msg']}>
      <div
        className={`${chatWorkspaceStyles['chat-avatar']}${error ? ' ' + chatWorkspaceStyles['error-avatar'] : ''}`}
      >
        {error ? '✕' : '✦'}
      </div>
      <div className={bubbleCls}>
        {text}
        {children}
      </div>
    </div>
  )
}
