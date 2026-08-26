import { memo } from 'react'
import type { ProjectSummary } from '../api/projectsApi'
import { documentTypeLabelFromWire } from '../../../shared/copy/documentTypeCopy'
import { ProjectFolderIcon } from './ProjectFolderIcon'
import { accentClass } from './projectAccent'
import { formatCardDate } from '../../../shared/lib/formatCardDate'
import { projectKey } from '../utils/projectKey'
import styles from './ProjectCard.module.css'
import projectsPageStyles from './ProjectsPage.module.css'
import { ProjectRetryControls } from './ProjectRetryControls'
import { MoreIcon } from './ProjectsIcons'
import type { RetryOverrides } from '../api/retryGenerationApi'

interface ProjectCardProps {
  project: ProjectSummary
  // Namespaces this card's testids so «Недавние проекты» and the full list below it can show the
  // same row without two elements answering to the same identity lookup.
  testIdPrefix?: string
  onOpen?: (project: ProjectSummary) => void
  onRetry?: (generationId: string, overrides?: RetryOverrides) => void
  retrying?: boolean
  retryError?: string | null
}

// One card. Two nested testids on purpose: `project-card` is what the feed is counted by, and
// `project-card-{kind}-{id}` is what an individual card is FETCHED by — identity, not position,
// because a positional lookup cannot fail on a swap.
function ProjectCardComponent({
  project,
  testIdPrefix,
  onOpen,
  retrying = false,
  retryError = null,
  onRetry,
}: ProjectCardProps) {
  const namespaced = (name: string) => (testIdPrefix ? `${testIdPrefix}-${name}` : name)
  const openable = onOpen !== undefined && project.kind === 'document'
  // An untitled document is labelled by the start of its own text, never by its type: naming every
  // untitled доклад "Доклад" is what made them indistinguishable in «Мои работы» and therefore
  // unopenable. It is also the open button's accessible name, so "" would leave the control
  // nameless — hence the fallback to the type label, which at least says what it opens.
  const label = project.title ?? project.preview ?? documentTypeLabelFromWire(project.documentType)
  return (
    <div
      className={`${projectsPageStyles['project-card']} ${accentClass(project.documentType)}${
        openable ? ' ' + styles['project-card-openable'] : ''
      }`}
      data-testid={namespaced('project-card')}
    >
      <div className={projectsPageStyles['project-card-thumb']}>
        <ProjectFolderIcon className={projectsPageStyles['project-card-folder']} />
      </div>
      <div
        className={projectsPageStyles['project-card-body']}
        data-testid={namespaced(`project-card-${projectKey(project)}`)}
      >
        {/* Бейдж и «···» в одной строке: мобильные фреймы дают карточке кнопку действий,
            которой в десктопной сетке нет (там действия живут в таблице вида списком).
            Кнопка рисуется всегда и скрывается CSS выше 720px — одна разметка на оба размера,
            иначе мобильная и десктопная карточка разъедутся молча. */}
        <div className={styles['project-card-head']}>
          {/* The LABEL the rest of the app uses ('Реферат'), never the wire's Cyrillic 'реферат':
              the history list shipped the raw field once and named one document two ways
              depending on which screen you looked at. */}
          <span
            className={projectsPageStyles['project-card-type']}
            data-testid={namespaced('project-card-type')}
          >
            {documentTypeLabelFromWire(project.documentType)}
          </span>
          {/* Меню за кнопкой — story 11 (переименовать / удалить / дублировать), у неё нет ни
              спеки, ни эндпоинтов. Пока это кнопка без меню, поэтому она `disabled`: видимая
              и явно недоступная честнее, чем та, что молча глотает нажатие. */}
          <button
            type="button"
            className={styles['project-card-more']}
            data-testid={namespaced('project-card-more')}
            aria-label="Действия над проектом"
            title="Действия появятся позже"
            disabled
          >
            <MoreIcon />
          </button>
        </div>
        {/* The whole card is the click target — that is what the ::after overlay on
            `.project-card-open` does — but the element that TAKES FOCUS and carries the
            accessible name is a real <button> around the title. A <div role="button"> would have
            to re-implement Enter and Space by hand, and a card without a title would announce
            itself as an unnamed button. */}
        <div
          className={projectsPageStyles['project-card-title']}
          data-testid={namespaced('project-card-title')}
        >
          {openable ? (
            <button
              type="button"
              className={styles['project-card-open']}
              onClick={() => onOpen!(project)}
            >
              {label}
            </button>
          ) : (
            label
          )}
        </div>
        <div
          className={projectsPageStyles['project-card-date']}
          data-testid={namespaced('project-card-date')}
        >
          {formatCardDate(project.updatedAt)}
        </div>
        {/* `retryable` is read as the server sent it and never recomputed from `status`: a client
            deriving it from an enum it may not fully know would offer the button on a status it
            does not recognise, which is fail-open on a paid operation. */}
        {project.retryable && onRetry !== undefined && (
          <ProjectRetryControls
            generationId={project.id}
            retrying={retrying}
            onRetry={onRetry}
            namespaced={namespaced}
          />
        )}
        {retryError !== null && (
          <p
            className={styles['project-card-retry-error']}
            data-testid={namespaced('project-card-retry-error')}
            role="alert"
          >
            {retryError}
          </p>
        )}
      </div>
    </div>
  )
}

// Memoized because the jury's remark was exactly this: any re-render of the list repainted every
// card. `ProjectsFeed` passes stable callbacks and a per-card `retrying`/`retryError` derived from
// ids, so a card re-renders when its own project or its own retry state changes — not when a
// sibling's does, and not when the toolbar's search box takes a keystroke.
export const ProjectCard = memo(ProjectCardComponent)
