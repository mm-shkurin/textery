import type { ProjectSummary } from '../api/projectsApi'
import type { ProjectView } from '../useProjectView'
import { ProjectCard, projectKey } from './ProjectCard'

interface ProjectsFeedProps {
  items: ProjectSummary[]
  view: ProjectView
  onOpen: (project: ProjectSummary) => void
  // Namespaces the cards' testids. «Недавние проекты» shows the same rows the full list below it
  // does, and two elements answering to `project-card-document-1` make an identity lookup
  // ambiguous — the one thing that testid exists to prevent.
  testIdPrefix?: string
}

/**
 * The cards, as a grid or as rows.
 *
 * The two views render the SAME components with a different class: switching is a re-render of
 * data already in hand, never a refetch, and a second component tree would be a second place for
 * a card to drift.
 */
export function ProjectsFeed({ items, view, onOpen, testIdPrefix }: ProjectsFeedProps) {
  return (
    <div
      className={`projects-page projects-view-${view}`}
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
        />
      ))}
    </div>
  )
}
