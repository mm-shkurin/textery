import { useProjectsFeed } from '../useProjectsFeed'
import { useProjectView } from '../useProjectView'
import { ProjectsNavbar } from './ProjectsNavbar'
import { ProjectsToolbar } from './ProjectsToolbar'
import { ProjectsEmptyState } from './ProjectsEmptyState'
import { ProjectsFeed } from './ProjectsFeed'
import { ProjectsPager } from './ProjectsPager'
import { useRetryGeneration } from '../useRetryGeneration'
import type { ProjectSummary } from '../api/projectsApi'
import './ProjectsPage.css'
import './ProjectsScreen.css'

// «Недавние проекты» is the first N items of the SAME response — never a second request for a
// slice of data already in hand. It is hidden under an active search or a non-default order,
// where "recent" stops describing what the section shows.
//
// Four, and the mobile layout shows two: the board's own note reads «в недавних проектах показ
// только последних 2 карточек (в вебе 4)». The narrowing is done in CSS rather than by branching
// on a measured viewport here — a JS breakpoint would render four cards, then drop two after the
// first paint, and would be wrong for the whole of a server render.
const RECENT_COUNT = 4

interface ProjectsPageProps {
  // Opening a card is the host's decision, not this screen's: the app reaches the editor through
  // flow state rather than through a URL, so a `navigate('/documents/{id}')` here would route to
  // a path that does not exist.
  // The wire document type travels with the id: the host needs it to pick the editor's labels,
  // and re-fetching the row it already has just to read one field would be a second request for
  // data on screen.
  onOpenDocument?: (documentId: string, wireDocumentType: string) => void
  onCreateProject?: () => void
  onBack?: () => void
  // Threaded from the flow rather than called here: signing out has to unwind the flow's step as
  // well as drop the tokens, and this screen knows nothing about either.
  onLogoutClick?: () => void
}

export function ProjectsPage({
  onOpenDocument,
  onCreateProject,
  onBack,
  onLogoutClick,
}: ProjectsPageProps = {}) {
  const feed = useProjectsFeed()
  const [view, setView] = useProjectView()
  const retry = useRetryGeneration(feed.reload)

  const searching = feed.q.trim() !== ''
  // The rail is part of the screen whenever there is anything to put in it. It shipped gated on
  // `items.length > RECENT_COUNT` — an argument against repeating cards the user can already see —
  // and that is not what the Figma frame draws: 484:1104 shows the rail above a list that repeats
  // it, at every size, and the mobile note treats it as a fixture of the screen too. The gate cost
  // a user with four projects the section entirely.
  //
  // Still hidden under an active search or a non-default order: there "recent" stops describing
  // what the section shows, and that reasoning survives the design.
  const showRecent = !searching && feed.sort === 'created_desc' && feed.items.length > 0

  const open = (project: ProjectSummary) => {
    // Only a document has an editor to open. A generation card is a record of work that never
    // became one, and its id comes from the other table entirely.
    if (project.kind === 'document') onOpenDocument?.(project.id, project.documentType)
  }

  return (
    <div className="projects-screen" data-testid="projects-screen">
      <ProjectsNavbar onLogoutClick={onLogoutClick} />

      <div className="projects-header">
        {onBack !== undefined && (
          <button
            type="button"
            className="projects-back"
            data-testid="projects-back"
            onClick={onBack}
          >
            Назад
          </button>
        )}
        <div className="projects-titles">
          <h1 className="projects-heading">Мои проекты</h1>
          {/* The one line of copy the screen has, and it is fixed rather than user-specific: it
              names what the page holds, which is why it can live in the markup. */}
          <p className="projects-subtitle" data-testid="projects-subtitle">
            Все ваши рефераты, курсовые, статьи и другие работы — в одном месте
          </p>
        </div>
      </div>

      <ProjectsToolbar
        q={feed.q}
        sort={feed.sort}
        view={view}
        resultCount={searching && !feed.loading && feed.error === null ? feed.total : null}
        onQueryChange={(q) => feed.update({ q })}
        onSortChange={(sort) => feed.update({ sort })}
        onViewChange={setView}
        onCreateProject={onCreateProject}
      />

      {feed.error !== null && (
        // `role="alert"` sits on the element carrying the sentence, not on an always-present
        // wrapper: an assistive-technology user hears the failure only if the words are inside
        // the live region at the moment it appears.
        <div className="projects-error-block">
          {/* The live region is the element carrying the SENTENCE, never a wrapper that also
              holds the retry button: an assistive-technology user would otherwise hear the
              failure and the word «Повторить» as one announcement, and any test reading the
              region's text would read the button's label as part of the message. */}
          <p className="projects-error" data-testid="projects-error" role="alert">
            {feed.error}
          </p>
          {/* Retrying re-issues the request with the SAME q and sort — a retry that reset them
              would answer a different question than the one that failed. */}
          <button type="button" data-testid="projects-error-retry" onClick={feed.reload}>
            Повторить
          </button>
        </div>
      )}

      {feed.loading && feed.error === null && (
        <div className="projects-skeleton" data-testid="projects-loading" aria-hidden="true">
          {Array.from({ length: RECENT_COUNT }, (_, index) => (
            <div className="projects-skeleton-card" key={index} />
          ))}
        </div>
      )}

      {showRecent && (
        <section className="projects-section projects-section-recent" data-testid="projects-recent">
          <h2 className="projects-section-title">Недавние проекты</h2>
          <ProjectsFeed
            items={feed.items.slice(0, RECENT_COUNT)}
            view="grid"
            onOpen={open}
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
          <h2 className="projects-section-title">Все проекты</h2>
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
              onOpen={open}
              onRetry={retry.retry}
              retryingId={retry.pendingId}
              retryError={retry.error}
            />
          )}
        </section>
      )}

      <ProjectsPager
        page={feed.page}
        limit={feed.limit}
        total={feed.total}
        onPage={(page) => feed.update({ page })}
      />
    </div>
  )
}
