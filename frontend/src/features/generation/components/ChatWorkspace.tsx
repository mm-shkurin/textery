import { useState } from 'react'
import styles from './GenerationScreen.module.css'
import './DocMarkdown.module.css'
import type { GenerationUiState } from '../hooks/useGeneration'
import { ComposerPanel } from './ComposerPanel'
import type { GenerationParameters } from '../utils/generationParameters'
import { DocArea } from './DocArea'
import { GenerationPending } from './GenerationPending'
import { GenerationSteps } from './GenerationSteps'
import { GenerationSummary } from './GenerationSummary'
import { AppHeader } from '../../../shared/components/AppHeader'
import { type DocumentType } from '../../../shared/domain/documentTypes'
import { topicFieldLabel } from '../../../shared/copy/documentTypeCopy'

interface ChatWorkspaceProps {
  documentType: DocumentType
  documentTypeLabel: string
  state: GenerationUiState
  content: string | null
  volumePages: number | null
  createdAt?: string | null
  error: string | null
  onSubmit: (topic: string, parameters: GenerationParameters) => void
  onReset: () => void
  onLogoutClick?: () => void
}

// Какой шаг горит на каждом состоянии прогона. `completed` — третий: экран с готовым
// документом пользователь видит только тогда, когда текста нет и редактор не открылся;
// шаг всё равно пройден. `failed` остаётся на втором — документа нет, и третий шаг был бы
// обещанием того, чего не случилось.
const STEP_BY_STATE: Record<GenerationUiState, 1 | 2 | 3> = {
  idle: 1,
  pending: 2,
  failed: 2,
  completed: 3,
}

/**
 * Экран генерации: форма темы и параметров, ожидание, результат.
 *
 * Перерисован по фрейму «Создание "Тип документа"» — мок
 * `ProductSpecification/stories/12-my-projects/mockups/live/07-generation-figma.html`.
 * Прежняя раскладка была двухколоночной: композер-панель слева, область документа справа,
 * а над ними бейдж состояния. Фрейм разворачивает её в одну колонку с шагами: пока тема не
 * отправлена, справа стоит сводка «Что будет в документе?», а не пустая область, в которой
 * до первой генерации нечего показывать.
 */
export function ChatWorkspace(props: ChatWorkspaceProps) {
  const { documentType, documentTypeLabel, state, content, volumePages, createdAt, error } = props
  const { onSubmit, onReset } = props
  const { onLogoutClick } = props
  const [draftId, setDraftId] = useState(0)

  const reset = () => {
    setDraftId((n) => n + 1)
    onReset()
  }

  return (
    <div className={styles['genform-page']}>
      <AppHeader onLogoutClick={onLogoutClick} />

      <div className={styles['genform-container']}>
        <div className={styles['genform-head']}>
          <h1 className={styles['genform-title']}>Создание «{documentTypeLabel}»</h1>
          <p className={styles['genform-subtitle']}>Укажите тему — Textery подготовит остальное</p>
        </div>

        <GenerationSteps current={STEP_BY_STATE[state]} />

        {state === 'idle' && (
          <div className={styles['genform-grid']}>
            <section className={styles['genform-card']} data-testid="generation-form">
              {/* key сбрасывает черновик после reset: топик живёт в состоянии композера, и
                  без пересоздания экран новой генерации возвращался бы с уже набранной темой
                  и активной кнопкой — один клик, и пользователь платит за тот же документ. */}
              <ComposerPanel
                key={draftId}
                topicLabel={topicFieldLabel(documentType)}
                documentType={documentType}
                onSubmit={onSubmit}
              />
            </section>
            <aside className={styles['genform-card']}>
              <GenerationSummary
                documentType={documentType}
                documentTypeLabel={documentTypeLabel}
              />
            </aside>
          </div>
        )}

        {state === 'pending' && <GenerationPending documentType={documentType} />}

        {/* Готово и ошибка — одна карточка на всю ширину: сводка «что будет в документе»
            после генерации отвечает на вопрос, который уже закрыт.
            Готовый документ виден здесь только когда текста нет и редактор не открылся сам
            (DocumentGenerationFlow) — то есть на пустом ответе, где показать нечего, но и
            молчать нельзя. */}
        {(state === 'completed' || state === 'failed') && (
          <section className={styles['genform-card']} data-testid="doc-area">
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
        )}
      </div>
    </div>
  )
}
