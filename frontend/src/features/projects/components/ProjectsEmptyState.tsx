import { SearchIcon } from './ProjectsIcons'
import styles from './ProjectsEmptyState.module.css'
import projectsToolbarStyles from './ProjectsToolbar.module.css'

interface ProjectsEmptyStateProps {
  searching: boolean
  onClearSearch: () => void
  onCreateProject?: () => void
}

/**
 * The feed with nothing in it.
 *
 * Two empty states, never one. "Nothing matched" offers to clear the query; "no work yet" offers
 * to create a project. Shipping one for both strands a new user on a search-reset button that does
 * nothing — and strands a searching user on a «Создать проект» that throws away their query.
 *
 * The no-work arm is drawn as the Figma frames «Мои проекты - после авторизации (нет проектов)»
 * (527:1863) and its Mobile twin (1141:12494) draw it: an illustration, a bold line naming the
 * state, a quiet line saying what to do, and the primary action. It shipped as a bare sentence and
 * an unstyled button, which reads as a page that failed to load rather than as an account that has
 * not started yet.
 */
export function ProjectsEmptyState({
  searching,
  onClearSearch,
  onCreateProject,
}: ProjectsEmptyStateProps) {
  if (searching) {
    return (
      <div className={styles['projects-empty']} data-testid="projects-empty-search">
        {/* Плитка с лупой, а не рисунок пустого ящика: это состояние про ЗАПРОС, и картинка
            «работ пока нет» соврала бы пользователю, у которого их двадцать. */}
        <span className={styles['projects-empty-glyph']} aria-hidden="true">
          <SearchIcon />
        </span>
        <p className={styles['projects-empty-title']}>Ничего не найдено.</p>
        <button
          type="button"
          className={styles['projects-empty-secondary']}
          data-testid="projects-clear-search"
          onClick={onClearSearch}
        >
          Сбросить поиск
        </button>
      </div>
    )
  }

  return (
    <div className={styles['projects-empty']} data-testid="projects-empty-none">
      {/* Decorative: the two lines below say everything the drawing says, so an alt text would
          make a screen reader announce the state twice. */}
      <img className={styles['projects-empty-art']} src="/design/projects-empty.png" alt="" />
      <p className={styles['projects-empty-title']}>Здесь пока ничего нет</p>
      <p className={styles['projects-empty-hint']}>Начните работу здесь</p>
      <button
        type="button"
        className={`${styles['projects-create-button']} ${projectsToolbarStyles['projects-create-button']}`}
        data-testid="projects-create"
        onClick={onCreateProject}
      >
        Создать проект
      </button>
    </div>
  )
}
