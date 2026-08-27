import type { ProjectSummary } from '../api/projectsApi'
import { ProjectCard } from './ProjectCard'
import { projectKey } from '../utils/projectKey'
import type { RetryOverrides } from '../api/retryGenerationApi'
import type { ProjectActions } from './ProjectCardMenu'
import projectsPageStyles from './ProjectsPage.module.css'

interface ProjectsFeedProps {
  items: ProjectSummary[]
  onOpen: (project: ProjectSummary) => void
  // Namespaces the cards' testids. «Недавние проекты» shows the same rows the full list below it
  // does, and two elements answering to `project-card-document-1` make an identity lookup
  // ambiguous — the one thing that testid exists to prevent.
  testIdPrefix?: string
  onRetry?: (generationId: string, overrides?: RetryOverrides) => void
  retryingId?: string | null
  retryError?: { id: string; message: string } | null
  actions?: ProjectActions
  actionError?: { id: string; message: string } | null
}

/**
 * Карточки сеткой.
 *
 * Вид списком больше не эта же сетка с другим классом — фрейм рисует там таблицу, и она живёт
 * в `ProjectsTable`. Переключение вида по-прежнему перерисовка данных, которые уже на руках,
 * а не новый запрос.
 */
export function ProjectsFeed({
  items,
  onOpen,
  testIdPrefix,
  onRetry,
  retryingId = null,
  retryError = null,
  actions,
  actionError = null,
}: ProjectsFeedProps) {
  return (
    <div
      className={projectsPageStyles['projects-page']}
      data-testid={testIdPrefix ? `${testIdPrefix}-projects-page` : 'projects-page'}
    >
      {items.map((project) => (
        // Keyed on `projectKey`, never on id alone — the two arms of the merged feed come from
        // different tables and their ids can collide.
        <ProjectCard
          key={projectKey(project)}
          project={project}
          testIdPrefix={testIdPrefix}
          onOpen={onOpen}
          onRetry={onRetry}
          retrying={retryingId === project.id}
          // Scoped to the card that failed: a page-level banner would leave the user hunting for
          // which of twenty cards the sentence is about.
          retryError={retryError?.id === project.id ? retryError.message : null}
          actions={actions}
          // Как и ошибка повтора — на карточке, которой она касается: общий баннер заставил бы
          // искать, о какой из двадцати строк речь.
          actionError={actionError?.id === project.id ? actionError.message : null}
        />
      ))}
    </div>
  )
}
