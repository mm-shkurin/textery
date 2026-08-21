import projectsScreenStyles from './ProjectsScreen.module.css'

interface ProjectsPageHeaderProps {
  // Absent when the host gives the screen no way back — the button is then not rendered at all
  // rather than rendered inert, so nothing on screen offers a route that does not exist.
  onBack?: () => void
}

// The screen's title block: the optional way back, the heading, and the one line of copy under it.
export function ProjectsPageHeader({ onBack }: ProjectsPageHeaderProps) {
  return (
    <div className={projectsScreenStyles['projects-header']}>
      {onBack !== undefined && (
        <button
          type="button"
          className={projectsScreenStyles['projects-back']}
          data-testid="projects-back"
          onClick={onBack}
        >
          Назад
        </button>
      )}
      <div className="projects-titles">
        <h1 className={projectsScreenStyles['projects-heading']}>Мои проекты</h1>
        {/* The one line of copy the screen has, and it is fixed rather than user-specific: it
          names what the page holds, which is why it can live in the markup. */}
        <p className={projectsScreenStyles['projects-subtitle']} data-testid="projects-subtitle">
          Все ваши рефераты, курсовые, статьи и другие работы — в одном месте
        </p>
      </div>
    </div>
  )
}
