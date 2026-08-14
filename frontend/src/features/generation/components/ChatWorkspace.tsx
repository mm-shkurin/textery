import { useState } from 'react'
import './ChatWorkspace.css'
import './ChatWorkspaceDoc.css'
import './DocMarkdown.css'
import type { GenerationUiState } from '../hooks/useGeneration'
import { Composer, MAX_TOPIC_LENGTH } from './Composer'
import { EMPTY_PARAMETERS, type GenerationParameters } from '../generationParameters'
import { Progress } from './Progress'
import { DocArea } from './DocArea'
import { GenerationHeading } from './GenerationHeading'
import { AppHeader } from '../../../shared/components/AppHeader'
import { type DocumentType } from '../../../shared/documentTypes'
import { topicFieldLabel } from '../../../shared/copy/documentTypeCopy'

interface ChatWorkspaceProps {
  // Both the id and its label, as ManualEditor already takes them: the label is what the
  // breadcrumb shows, while the composer's heading needs the genitive form, which only the id
  // can look up.
  documentType: DocumentType
  documentTypeLabel: string
  state: GenerationUiState
  content: string | null
  volumePages: number | null
  createdAt?: string | null
  error: string | null
  onSubmit: (topic: string, parameters: GenerationParameters) => void
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
  const { documentType, documentTypeLabel, state, content, volumePages, createdAt, error } = props
  const { onSubmit, onReset } = props
  const { onLogoutClick } = props
  const [topic, setTopic] = useState('')
  const [parameters, setParameters] = useState<GenerationParameters>(EMPTY_PARAMETERS)

  const send = () => {
    const trimmed = topic.trim().slice(0, MAX_TOPIC_LENGTH)
    if (trimmed) onSubmit(trimmed, parameters)
  }

  // The topic lives in this component's state, so `useGeneration.reset()` cannot reach it — it
  // clears the generation, and the workspace is never unmounted across a reset (only the idle
  // branch swaps Progress back for Composer). Without this the "Создать новый доклад" screen
  // came back pre-filled with the topic that was just generated, send button already enabled:
  // one keystroke re-bills the user for the document they already have. Clearing here keeps the
  // topic owned by the one component that holds it.
  const reset = () => {
    setTopic('')
    // The parameters are cleared with the topic and for the same reason: a "Создать новый"
    // screen carrying the previous run's требования and объём invites one keystroke to re-bill
    // the user for a document they already have, this time with settings they never re-read.
    setParameters(EMPTY_PARAMETERS)
    onReset()
  }

  return (
    <div className="chat-page">
      <AppHeader onLogoutClick={onLogoutClick} />
      <div className="cw-container">
        {/* Two different mockups own this slot. Before anything is submitted the surface is
            mockup 04 (breadcrumb naming the picked type + page title); from the moment a
            generation exists it is mockups 05-07, whose status badge tells the user where the
            run stands. Showing both at once would state the obvious twice. */}
        {state === 'idle' ? (
          <GenerationHeading documentTypeLabel={documentTypeLabel} />
        ) : (
          <div className={`cw-badge cw-badge-${state}`}>
            <span className="cw-dot" />
            {BADGE[state]}
          </div>
        )}
        <div className="cw-layout">
          <aside className="chat-panel" data-testid="chat-panel">
            {state === 'idle' ? (
              <Composer
                topicLabel={topicFieldLabel(documentType)}
                topic={topic}
                parameters={parameters}
                setParameters={setParameters}
                setTopic={setTopic}
                onSend={send}
              />
            ) : (
              <Progress state={state} documentType={documentType} />
            )}
          </aside>
          <section className="doc-area" data-testid="doc-area">
            <DocArea
              state={state}
              content={content}
              volumePages={volumePages}
              createdAt={createdAt ?? null}
              error={error}
              documentType={documentType}
              label={documentTypeLabel}
              onReset={reset}
            />
          </section>
        </div>
      </div>
    </div>
  )
}
