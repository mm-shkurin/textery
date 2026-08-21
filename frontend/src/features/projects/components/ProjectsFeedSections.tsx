import type { ProjectSummary } from '../api/projectsApi'
import type { useProjectsFeed } from '../hooks/useProjectsFeed'
import type { useRetryGeneration } from '../hooks/useRetryGeneration'
import type { ProjectView } from '../hooks/useProjectView'
import { ProjectsEmptyState } from './ProjectsEmptyState'
import { ProjectsFeed } from './ProjectsFeed'
import projectsScreenStyles from './ProjectsScreen.module.css'
import projectsPageStyles from './ProjectsPage.module.css'

// «Недавние проекты» is the first N items of the SAME response — never a second request for a
// slice of data already in hand. It is hidden under an active search or a non-default order,
// where "recent" stops describing what the section shows.
//
// Four, and the mobile layout shows two: the board's own note reads «в недавних проектах показ
// только последних 2 карточек (в вебе 4)». The narrowing is done in CSS rather than by branching
// on a measured viewport here — a JS breakpoint would render four cards, then drop two after the
// first paint, and would be wrong for the whole of a server render.
export const RECENT_COUNT = 4

type Feed = ReturnType<typeof useProjectsFeed>
type Retry = ReturnType<typeof useRetryGeneration>

interface ProjectsFeedSectionsProps {
  feed: Feed
  view: ProjectView
  searching: boolean
  retry: Retry
  onOpen: (project: ProjectSummary) => void
  onCreateProject?: () => void
}

// The failure banner. `role="alert"` sits on the element carrying the sentence, not on an
// always-present wrapper: an assistive-technology user hears the failure only if the words are
// inside the live region at the moment it appears.
function ProjectsErrorBlock({ message, onReload }: { message: string; onReload: () => void }) {
  return (
    <div className={projectsScreenStyles['projects-error-block']}>
      {/* The live region is the element carrying the SENTENCE, never a wrapper that also
        holds the retry button: an assistive-technology user would otherwise hear the
        failure and the word «Повторить» as one announcement, and any test reading the
        region's text would read the button's label as part of the message. */}
      <p className={projectsPageStyles['projects-error']} data-testid="projects-error" role="alert">
        {message}
      </p>
      {/* Retrying re-issues the request with the SAME q and sort — a retry that reset them
        would answer a different question than the one that failed. */}
      <button type="button" data-testid="projects-error-retry" onClick={onReload}>
        Повторить
      </button>
    </div>
  )
}

function ProjectsSkeleton() {
  return (
    <div
      className={projectsScreenStyles['projects-skeleton']}
      data-testid="projects-loading"
      aria-hidden="true"
    >
      {Array.from({ length: RECENT_COUNT }, (_, index) => (
        <div className={projectsScreenStyles['projects-skeleton-card']} key={index} />
      ))}
    </div>
  )
}

// The rail is part of the screen whenever there is anything to put in it. It shipped gated on
// `items.length > RECENT_COUNT` — an argument against repeating cards the user can already see —
// and that is not what the Figma frame draws: 484:1104 shows the rail above a list that repeats
// it, at every size, and the mobile note treats it as a fixture of the screen too. The gate cost
// a user with four projects the section entirely.
//
// Still hidden under an active search or a non-default order: there "recent" stops describing
// what the section shows, and that reasoning survives the design.
function showsRecent(feed: Feed, searching: boolean): boolean {
  return !searching && feed.sort === 'created_desc' && feed.items.length > 0
}

// Everything between the toolbar and the pager: the failure, the loading placeholder, the recent
// rail and the full list. One component because they are four renderings of ONE question — what
// the feed currently is — and reading them together is the only way to see that exactly one of
// them can be on screen at a time.
export function ProjectsFeedSections({
  feed,
  view,
  searching,
  retry,
  onOpen,
  onCreateProject,
}: ProjectsFeedSectionsProps) {
  return (
    <>
      {feed.error !== null && <ProjectsErrorBlock message={feed.error} onReload={feed.reload} />}

      {feed.loading && feed.error === null && <ProjectsSkeleton />}

      {showsRecent(feed, searching) && (
        <section
          className={`projects-section ${projectsPageStyles['projects-section-recent']}`}
          data-testid="projects-recent"
        >
          <h2 className={projectsScreenStyles['projects-section-title']}>Недавние проекты</h2>
          <ProjectsFeed
            items={feed.items.slice(0, RECENT_COUNT)}
            view="grid"
            onOpen={onOpen}
            testIdPrefix="recent"
          />
        </section>
      )}

      {/* The heading stands whether or not the feed under it has rows — the empty frame
        (527:1863) draws «Все проекты» above the illustration. It is the answer to "where am I",
        and a screen that drops its only structural landmark exactly when there is nothing else
        on it leaves the user with a page of whitespace. Held back only while the feed is
        unresolved: heading a section that turns out to be a load failure would title the error. */}
      {feed.error === null && !feed.loading && (
        <section className="projects-section">
          <h2 className={projectsScreenStyles['projects-section-title']}>Все проекты</h2>
          {feed.items.length === 0 ? (
            <ProjectsEmptyState
              searching={searching}
              onClearSearch={() => feed.update({ q: '' })}
              onCreateProject={onCreateProject}
            />
          ) : (
            <ProjectsFeed
              items={feed.items}
              view={view}
              onOpen={onOpen}
              onRetry={retry.retry}
              retryingId={retry.pendingId}
              retryError={retry.error}
            />
          )}
        </section>
      )}
    </>
  )
}
