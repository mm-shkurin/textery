import type { ProjectView } from '../hooks/useProjectView'
import { SparkleIcon } from './ProjectsIcons'
import {
  ProjectsSearchField,
  ProjectsSortSelect,
  ProjectsViewToggle,
  ProjectsFilterButton,
} from './ProjectsToolbarControls'
import styles from './ProjectsToolbar.module.css'
import projectsEmptyStateStyles from './ProjectsEmptyState.module.css'

interface ProjectsToolbarProps {
  q: string
  sort: string
  view: ProjectView
  resultCount: number | null
  onQueryChange: (q: string) => void
  onSortChange: (sort: string) => void
  onViewChange: (view: ProjectView) => void
  // The toolbar's «Создать проект» — the Figma frames put the primary action HERE, on every state
  // of the screen, not only inside the empty state. A user with twenty projects otherwise has no
  // way to start a twenty-first without emptying the feed first.
  onCreateProject?: () => void
}

// The count is rendered only while a search is active: on the unfiltered feed it would restate
// the number of cards the user is already looking at.
function ProjectsResultCount({ resultCount }: { resultCount: number | null }) {
  if (resultCount === null) return null
  return (
    <span className={styles['projects-result-count']} data-testid="projects-result-count">
      Найдено: {resultCount}
    </span>
  )
}

function ProjectsCreateButton({ onCreateProject }: { onCreateProject?: () => void }) {
  if (onCreateProject === undefined) return null
  return (
    <button
      type="button"
      className={`${projectsEmptyStateStyles['projects-create-button']} ${styles['projects-create-button']}`}
      data-testid="projects-toolbar-create"
      onClick={onCreateProject}
    >
      <SparkleIcon className={styles['projects-create-sparkle']} />
      Создать проект
    </button>
  )
}

export function ProjectsToolbar({
  q,
  sort,
  view,
  resultCount,
  onQueryChange,
  onSortChange,
  onViewChange,
  onCreateProject,
}: ProjectsToolbarProps) {
  return (
    <div className={styles['projects-toolbar']} data-testid="projects-toolbar">
      <div className={styles['projects-toolbar-filters']}>
        <ProjectsSearchField q={q} onQueryChange={onQueryChange} />
        <ProjectsFilterButton />
        <ProjectsSortSelect sort={sort} onSortChange={onSortChange} />
        <ProjectsResultCount resultCount={resultCount} />
      </div>

      <div className={styles['projects-toolbar-actions']}>
        <ProjectsCreateButton onCreateProject={onCreateProject} />
        <ProjectsViewToggle view={view} onViewChange={onViewChange} />
      </div>
    </div>
  )
}
