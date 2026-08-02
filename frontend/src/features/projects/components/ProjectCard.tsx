import type { ProjectSummary } from '../api/projectsApi'
import { documentTypeLabelFromWire } from '../../../shared/documentTypes'

interface ProjectCardProps {
  project: ProjectSummary
}

// One card. Two nested testids on purpose: `project-card` is what the feed is counted by, and
// `project-card-{kind}-{id}` is what an individual card is FETCHED by — identity, not position,
// because the two arms' ids collide and a positional lookup cannot fail on a swap.
export function ProjectCard({ project }: ProjectCardProps) {
  return (
    <div className="project-card" data-testid="project-card">
      <div className="project-card-body" data-testid={`project-card-${project.kind}-${project.id}`}>
        {/* The LABEL the rest of the app uses ('Реферат'), never the wire's Cyrillic 'реферат':
            the history list shipped the raw field once and named one document two ways
            depending on which screen you looked at. */}
        <div className="project-card-type" data-testid="project-card-type">
          {documentTypeLabelFromWire(project.documentType)}
        </div>
        <div className="project-card-title" data-testid="project-card-title">
          {project.title}
        </div>
        <div className="project-card-date" data-testid="project-card-date">
          {formatCardDate(project.updatedAt)}
        </div>
      </div>
    </div>
  )
}

// Day + month, no year — the format the mockup renders (`<div class="date">15 июля</div>`). The
// wire sends UTC ISO; toLocaleDateString renders it in the reader's zone.
function formatCardDate(iso: string): string {
  return new Date(iso).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' })
}
