import { useState } from 'react'
import styles from './ChatWorkspace.module.css'
import chatWorkspaceDocStyles from './ChatWorkspaceDoc.module.css'
import './DocMarkdown.module.css'
import type { GenerationUiState } from '../hooks/useGeneration'
import { ComposerPanel } from './ComposerPanel'
import type { GenerationParameters } from '../utils/generationParameters'
import { Progress } from './Progress'
import { DocArea } from './DocArea'
import { GenerationHeading } from './GenerationHeading'
import { AppHeader } from '../../../shared/components/AppHeader'
import { type DocumentType } from '../../../shared/domain/documentTypes'
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
  // Identifies the current draft. The workspace is never unmounted across a reset — only the
  // idle branch swaps Progress back for the composer — so without this the «Создать новый
  // доклад» screen came back pre-filled with the topic that was just generated, send button
  // already enabled: one keystroke re-bills the user for the document they already have.
  //
  // A nonce rather than a `setTopic('')` reaching down: the draft now belongs to ComposerPanel,
  // and remounting it is how an owner discards a draft without reading it first. The parameters
  // — требования and объём — go with the topic, for the same re-billing reason.
  const [draftId, setDraftId] = useState(0)

  const reset = () => {
    setDraftId((n) => n + 1)
    onReset()
  }

  return (
    <div className={styles['chat-page']}>
      <AppHeader onLogoutClick={onLogoutClick} />
      <div className={styles['cw-container']}>
        {/* Two different mockups own this slot. Before anything is submitted the surface is
            mockup 04 (breadcrumb naming the picked type + page title); from the moment a
            generation exists it is mockups 05-07, whose status badge tells the user where the
            run stands. Showing both at once would state the obvious twice. */}
        {state === 'idle' ? (
          <GenerationHeading documentTypeLabel={documentTypeLabel} />
        ) : (
          <div className={`${styles['cw-badge']} ${styles[`cw-badge-${state}`]}`}>
            <span className={styles['cw-dot']} />
            {BADGE[state]}
          </div>
        )}
        <div className={styles['cw-layout']}>
          <aside className={styles['chat-panel']} data-testid="chat-panel">
            {state === 'idle' ? (
              <ComposerPanel
                key={draftId}
                topicLabel={topicFieldLabel(documentType)}
                documentType={documentType}
                onSubmit={onSubmit}
              />
            ) : (
              <Progress state={state} documentType={documentType} />
            )}
          </aside>
          <section
            className={`${styles['doc-area']} ${chatWorkspaceDocStyles['doc-area']}`}
            data-testid="doc-area"
          >
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
