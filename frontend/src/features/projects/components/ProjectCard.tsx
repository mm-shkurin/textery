import type { ProjectSummary } from '../api/projectsApi'
import {
  documentTypeFromWire,
  documentTypeLabelFromWire,
  type DocumentType,
} from '../../../shared/documentTypes'
import { ProjectFolderIcon } from './ProjectFolderIcon'

interface ProjectCardProps {
  project: ProjectSummary
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
export function ProjectCard({ project }: ProjectCardProps) {
  return (
    <div className={`project-card ${accentClass(project.documentType)}`} data-testid="project-card">
      <div className="project-card-thumb">
        <ProjectFolderIcon className="project-card-folder" />
      </div>
      <div className="project-card-body" data-testid={`project-card-${projectKey(project)}`}>
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

// Day + month for this year, day + month + year for anything older — both formats are in the
// mockup (`15 июля` alongside `2 сентября 2025` and `16 декабря 2024`). Dropping the year
// unconditionally would render a 2024 project as `16 декабря`, indistinguishable from one
// finished this month, on the screen whose whole job is telling the user's work apart.
//
// The wire sends UTC ISO; toLocaleDateString renders it in the reader's zone, and the year is
// compared in that same zone so a 31 December evening does not read as next year's.
//
// The year is appended by hand rather than asked of the formatter: ru-RU's `year: 'numeric'`
// emits the era suffix ('2 сентября 2025 г.') and the mockup does not. The formatter still owns
// the day and the genitive month, which is the part worth not hand-rolling.
//
// `updatedAt: string` is a compile-time claim about a runtime JSON body from an endpoint the
// backend has not built, so both guards below are about values the type system says cannot arrive.
// The INPUT is guarded, not the resulting epoch value: `new Date(null)` is a perfectly valid Date
// reading 1 января 1970, which no `isNaN` check catches and which the user reads as a real edit
// date. A `getTime() === 0` guard would satisfy the same two tests while blanking a genuine
// 1970-01-01 — a different bug. `—` rather than an empty slot, matching `HistoryPage`'s
// `formatDate`, which has shipped that placeholder for the same condition since before this screen.
const UNUSABLE_DATE = '—'

// A backend sentinel (`0001-01-01T00:00:00Z`, `9999-12-31T23:59:59Z` — what LocalDate.MIN,
// datetime.min and DateTime.MaxValue serialize to when a nullable column is mapped through a
// non-nullable field) arrives as a perfectly shaped, perfectly parseable ISO string. Neither shape
// guard above can see it; only its VALUE is wrong. So the year is bounded.
//
// The bounds are fixed constants, deliberately generous, and NOT derived from the current clock.
// `new Date().getFullYear()` as the ceiling would blank the date of a project the user edited
// seconds ago whenever their clock runs minutes behind the server's, and would do it to every
// project on every 31 December evening. The floor sits strictly below 1970 because
// `1970-01-01T00:00:00Z` is a genuinely renderable instant whose `getFullYear()` is 1969 in any
// negative-offset zone — a floor AT 1970 would blank a real date.
const EARLIEST_PLAUSIBLE_YEAR = 1900
const LATEST_PLAUSIBLE_YEAR = 2200

function formatCardDate(iso: string): string {
  if (typeof iso !== 'string') return UNUSABLE_DATE
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return UNUSABLE_DATE
  const parsedYear = date.getFullYear()
  if (parsedYear < EARLIEST_PLAUSIBLE_YEAR || parsedYear > LATEST_PLAUSIBLE_YEAR) {
    return UNUSABLE_DATE
  }
  const dayAndMonth = date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' })
  const showYear = parsedYear !== new Date().getFullYear()
  return showYear ? `${dayAndMonth} ${parsedYear}` : dayAndMonth
}
