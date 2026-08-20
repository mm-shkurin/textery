import { memo } from 'react'
import type { ProjectSummary } from '../api/projectsApi'
import { documentTypeFromWire, type DocumentType } from '../../../shared/documentTypes'
import { documentTypeLabelFromWire } from '../../../shared/copy/documentTypeCopy'
import { ProjectFolderIcon } from './ProjectFolderIcon'
import { formatCardDate } from '../../../shared/formatCardDate'
import { projectKey } from '../utils/projectKey'
import styles from './ProjectCard.module.css'
import projectsPageStyles from './ProjectsPage.module.css'
import projectsScreenStyles from './ProjectsScreen.module.css'
import { ProjectRetryControls } from './ProjectRetryControls'
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

// The mockup tints each card by document type — badge fill, badge text and folder glyph move
// together — so the type picks ONE accent name and the stylesheet owns the three colours. Written
// as a table rather than a chain of ternaries because it is exhaustive on DocumentType: adding a
// type without an accent is a compile error here, in the file that has to know.
// Read off the Figma frame «Мои проекты - вид сетка - вариант 1 (Dekstop)» (node 484:1104), one
// accent per type — эссе is coral there, not teal. It shipped as teal, which gave эссе and
// сочинение the same badge and the same folder: two document types a user cannot tell apart at a
// glance is exactly the confusion the tint exists to prevent.
const ACCENT_BY_TYPE: Record<DocumentType, string> = {
  referat: 'blue',
  doklad: 'purple',
  sochinenie: 'teal',
  essay: 'coral',
}

// A type this client has never heard of still gets a card. Blue is the mockup's most common tint
// and the least-surprising default; the alternative — no accent class — would render an unstyled
// transparent badge, which reads as a broken card rather than an unfamiliar one.
function accentClass(wireDocumentType: string): string {
  const appType = documentTypeFromWire(wireDocumentType)
  return projectsPageStyles[`project-card-accent-${appType ? ACCENT_BY_TYPE[appType] : 'blue'}`]
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
      className={`${projectsPageStyles['project-card']} ${projectsScreenStyles['project-card']} ${accentClass(project.documentType)}${
        openable ? ' ' + styles['project-card-openable'] : ''
      }`}
      data-testid={namespaced('project-card')}
    >
      <div
        className={`${projectsPageStyles['project-card-thumb']} ${projectsScreenStyles['project-card-thumb']}`}
      >
        <ProjectFolderIcon className={projectsPageStyles['project-card-folder']} />
      </div>
      <div
        className={`${projectsPageStyles['project-card-body']} ${projectsScreenStyles['project-card-body']}`}
        data-testid={namespaced(`project-card-${projectKey(project)}`)}
      >
        {/* The LABEL the rest of the app uses ('Реферат'), never the wire's Cyrillic 'реферат':
            the history list shipped the raw field once and named one document two ways
            depending on which screen you looked at. */}
        <div
          className={projectsPageStyles['project-card-type']}
          data-testid={namespaced('project-card-type')}
        >
          {documentTypeLabelFromWire(project.documentType)}
        </div>
        {/* The whole card is the click target — that is what the ::after overlay on
            `.project-card-open` does — but the element that TAKES FOCUS and carries the
            accessible name is a real <button> around the title. A <div role="button"> would have
            to re-implement Enter and Space by hand, and a card without a title would announce
            itself as an unnamed button. */}
        <div
          className={`${projectsPageStyles['project-card-title']} ${projectsScreenStyles['project-card-title']}`}
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
