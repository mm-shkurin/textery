import type { ProjectSummary } from '../api/projectsApi'
import { documentTypeLabelFromWire } from '../../../shared/copy/documentTypeCopy'
import { formatCardDate } from '../../../shared/lib/formatCardDate'
import { projectKey } from '../utils/projectKey'
import { accentClass } from './projectAccent'
import { ProjectFolderIcon } from './ProjectFolderIcon'
import { ProjectCardMenu, type ProjectActions } from './ProjectCardMenu'
import styles from './ProjectsTable.module.css'
import projectsPageStyles from './ProjectsPage.module.css'

interface ProjectsTableProps {
  items: ProjectSummary[]
  onOpen: (project: ProjectSummary) => void
  // Namespaces the rows' testids, exactly as the grid does: «Недавние проекты» shows the same
  // rows the full list below it does, and two elements answering to one identity lookup is the
  // one thing a testid exists to prevent.
  testIdPrefix?: string
  actions?: ProjectActions
}

function ProjectsTableRow({
  project,
  onOpen,
  namespaced,
  actions,
}: {
  project: ProjectSummary
  onOpen: (project: ProjectSummary) => void
  namespaced: (name: string) => string
  actions?: ProjectActions
}) {
  const openable = project.kind === 'document'
  const label = project.title ?? project.preview ?? documentTypeLabelFromWire(project.documentType)
  return (
    <tr data-testid={namespaced('project-card')}>
      <td data-testid={namespaced(`project-card-${projectKey(project)}`)}>
        <div className={styles['projects-row-name']}>
          <span className={`${styles['projects-row-thumb']} ${accentClass(project.documentType)}`}>
            <ProjectFolderIcon className={projectsPageStyles['project-card-folder']} />
          </span>
          {/* Открывает документ только та строка, за которой документ есть: генерация — запись
              о работе, которая им так и не стала, и редактора у неё нет. Кнопка, а не строка с
              onClick: Enter и Space должна обрабатывать платформа. */}
          {openable ? (
            <button
              type="button"
              className={styles['projects-row-title']}
              data-testid={namespaced('project-card-title')}
              onClick={() => onOpen(project)}
            >
              {label}
            </button>
          ) : (
            <span
              className={styles['projects-row-title']}
              data-testid={namespaced('project-card-title')}
            >
              {label}
            </span>
          )}
        </div>
      </td>
      <td className={accentClass(project.documentType)}>
        <span
          className={projectsPageStyles['project-card-type']}
          data-testid={namespaced('project-card-type')}
        >
          {documentTypeLabelFromWire(project.documentType)}
        </span>
      </td>
      <td className={styles['projects-row-date']} data-testid={namespaced('project-card-date')}>
        {formatCardDate(project.updatedAt)}
      </td>
      <td>
        {/* То же меню, что на карточке: переименовать или удалить. У генерации его нет —
            удалять и переименовать нечего. */}
        {actions !== undefined && project.kind === 'document' && (
          <ProjectCardMenu
            documentId={project.id}
            title={label}
            testId={namespaced('project-card-menu')}
            onRename={actions.onRename}
            onDelete={actions.onDelete}
            busy={actions.busy}
          />
        )}
      </td>
    </tr>
  )
}

/**
 * Вид списком.
 *
 * Это ТАБЛИЦА, а не те же карточки в одну колонку: фрейм «Мои проекты — вид списком — вариант 1»
 * рисует шапку столбцов (Название / Тип / Дата создания), плитку с иконкой типа, бейдж и «···».
 * Столбцы — это столбцы, поэтому `<table>`: скринридер объявляет заголовок колонки вместе со
 * значением, чего набор `<div>` с теми же рамками не даёт.
 */
export function ProjectsTable({ items, onOpen, testIdPrefix, actions }: ProjectsTableProps) {
  const namespaced = (name: string) => (testIdPrefix ? `${testIdPrefix}-${name}` : name)
  return (
    <table
      className={styles['projects-table']}
      data-testid={testIdPrefix ? `${testIdPrefix}-projects-page` : 'projects-page'}
    >
      <thead>
        <tr>
          <th>Название</th>
          <th className={styles['projects-table-type']}>Тип</th>
          <th className={styles['projects-table-date']}>Дата создания</th>
          {/* Столбец действий заголовка не имеет: подписывать колонку с одной кнопкой в каждой
              строке нечем, а пустой `<th>` держит сетку. */}
          <th className={styles['projects-table-actions']} aria-label="Действия" />
        </tr>
      </thead>
      <tbody>
        {items.map((project) => (
          // Ключ по `projectKey`, а не по id: две ветки ленты приходят из разных таблиц и их id
          // могут совпасть.
          <ProjectsTableRow
            key={projectKey(project)}
            project={project}
            onOpen={onOpen}
            namespaced={namespaced}
            actions={actions}
          />
        ))}
      </tbody>
    </table>
  )
}
