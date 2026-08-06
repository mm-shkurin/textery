import type { ProjectSummary } from '../api/projectsApi'
import type { ProjectView } from '../useProjectView'
import { ProjectCard } from './ProjectCard'
import { projectKey } from '../projectKey'

interface ProjectsFeedProps {
  items: ProjectSummary[]
  view: ProjectView
  onOpen: (project: ProjectSummary) => void
  // Namespaces the cards' testids. «Недавние проекты» shows the same rows the full list below it
  // does, and two elements answering to `project-card-document-1` make an identity lookup
  // ambiguous — the one thing that testid exists to prevent.
  testIdPrefix?: string
  onRetry?: (generationId: string) => void
  retryingId?: string | null
  retryError?: { id: string; message: string } | null
}

/**
 * The cards, as a grid or as rows.
 *
 * The two views render the SAME components with a different class: switching is a re-render of
 * data already in hand, never a refetch, and a second component tree would be a second place for
 * a card to drift.
 */
export function ProjectsFeed({
  items,
  view,
  onOpen,
  testIdPrefix,
  onRetry,
  retryingId = null,
  retryError = null,
}: ProjectsFeedProps) {
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
          onRetry={onRetry}
          retrying={retryingId === project.id}
          // Scoped to the card that failed: a page-level banner would leave the user hunting for
          // which of twenty cards the sentence is about.
          retryError={retryError?.id === project.id ? retryError.message : null}
        />
      ))}
    </div>
  )
}
