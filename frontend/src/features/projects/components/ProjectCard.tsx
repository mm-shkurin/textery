import type { ProjectSummary } from '../api/projectsApi'
import {
  documentTypeFromWire,
  documentTypeLabelFromWire,
  type DocumentType,
} from '../../../shared/documentTypes'
import { ProjectFolderIcon } from './ProjectFolderIcon'
import { formatCardDate } from '../formatCardDate'

interface ProjectCardProps {
  project: ProjectSummary
  // Namespaces this card's testids so «Недавние проекты» and the full list below it can show the
  // same row without two elements answering to the same identity lookup.
  testIdPrefix?: string
  onOpen?: (project: ProjectSummary) => void
}

// A project's identity, in one place because both consumers of it explain the same hazard: the
// two arms of the merged feed come from different tables, so `id` alone is NOT unique — the
// fixture's document and generation both carry id '1'. Keying or addressing a card on `id` would
// collapse the pair onto one node. Named here so the rule is stated once rather than re-derived
// as an inline template literal at each site.
export function projectKey(project: ProjectSummary): string {
  return `${project.kind}-${project.id}`
}

// The mockup tints each card by document type — badge fill, badge text and folder glyph move
// together — so the type picks ONE accent name and the stylesheet owns the three colours. Written
// as a table rather than a chain of ternaries because it is exhaustive on DocumentType: adding a
// type without an accent is a compile error here, in the file that has to know.
const ACCENT_BY_TYPE: Record<DocumentType, string> = {
  referat: 'blue',
  doklad: 'purple',
  sochinenie: 'teal',
  essay: 'teal',
}

// A type this client has never heard of still gets a card. Blue is the mockup's most common tint
// and the least-surprising default; the alternative — no accent class — would render an unstyled
// transparent badge, which reads as a broken card rather than an unfamiliar one.
function accentClass(wireDocumentType: string): string {
  const appType = documentTypeFromWire(wireDocumentType)
  return `project-card-accent-${appType ? ACCENT_BY_TYPE[appType] : 'blue'}`
}

// One card. Two nested testids on purpose: `project-card` is what the feed is counted by, and
// `project-card-{kind}-{id}` is what an individual card is FETCHED by — identity, not position,
// because a positional lookup cannot fail on a swap.
export function ProjectCard({ project, testIdPrefix, onOpen }: ProjectCardProps) {
  const namespaced = (name: string) => (testIdPrefix ? `${testIdPrefix}-${name}` : name)
  const openable = onOpen !== undefined && project.kind === 'document'
  return (
    <div
      className={`project-card ${accentClass(project.documentType)}${openable ? ' project-card-openable' : ''}`}
      data-testid={namespaced('project-card')}
      // A card is opened by click and by keyboard alike. `role="button"` + `tabIndex` rather than
      // a real <button>: the card carries block content, and a button element would put a
      // heading and a date inside interactive phrasing content.
      role={openable ? 'button' : undefined}
      tabIndex={openable ? 0 : undefined}
      onClick={openable ? () => onOpen!(project) : undefined}
      onKeyDown={
        openable
          ? (event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault()
                onOpen!(project)
              }
            }
          : undefined
      }
    >
      <div className="project-card-thumb">
        <ProjectFolderIcon className="project-card-folder" />
      </div>
      <div className="project-card-body" data-testid={namespaced(`project-card-${projectKey(project)}`)}>
        {/* The LABEL the rest of the app uses ('Реферат'), never the wire's Cyrillic 'реферат':
            the history list shipped the raw field once and named one document two ways
            depending on which screen you looked at. */}
        <div className="project-card-type" data-testid={namespaced('project-card-type')}>
          {documentTypeLabelFromWire(project.documentType)}
        </div>
        <div className="project-card-title" data-testid={namespaced('project-card-title')}>
          {/* An untitled document is labelled by the start of its own text, never by its type:
              naming every untitled доклад "Доклад" is what made them indistinguishable in «Мои
              работы» and therefore unopenable. */}
          {project.title ?? project.preview ?? ''}
        </div>
        <div className="project-card-date" data-testid={namespaced('project-card-date')}>
          {formatCardDate(project.updatedAt)}
        </div>
      </div>
    </div>
  )
}
