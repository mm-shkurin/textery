import { useProjectsFeed } from '../useProjectsFeed'
import { useProjectView } from '../useProjectView'
import { ProjectsToolbar } from './ProjectsToolbar'
import { ProjectsFeed } from './ProjectsFeed'
import { ProjectsPager } from './ProjectsPager'
import type { ProjectSummary } from '../api/projectsApi'
import './ProjectsPage.css'
import './ProjectsScreen.css'

// «Недавние проекты» is the first N items of the SAME response — never a second request for a
// slice of data already in hand. It is hidden under an active search or a non-default order,
// where "recent" stops describing what the section shows.
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
}

export function ProjectsPage({ onOpenDocument, onCreateProject, onBack }: ProjectsPageProps = {}) {
  const feed = useProjectsFeed()
  const [view, setView] = useProjectView()

  const searching = feed.q.trim() !== ''
  // Only worth a section when it is a shortcut to something not already on screen. The mockup
  // draws «Недавние проекты» above a list that repeats them; repeating four cards a user can
  // already see costs a screenful and buys nothing, so the section appears once the page holds
  // more than it would show.
  const showRecent =
    !searching && feed.sort === 'created_desc' && feed.items.length > RECENT_COUNT

  const open = (project: ProjectSummary) => {
    // Only a document has an editor to open. A generation card is a record of work that never
    // became one, and its id comes from the other table entirely.
    if (project.kind === 'document') onOpenDocument?.(project.id, project.documentType)
  }

  return (
    <div className="projects-screen" data-testid="projects-screen">
      <div className="projects-header">
        {onBack !== undefined && (
          <button type="button" className="projects-back" data-testid="projects-back" onClick={onBack}>
            Назад
          </button>
        )}
        <h1 className="projects-heading">Мои проекты</h1>
      </div>

      <ProjectsToolbar
        q={feed.q}
        sort={feed.sort}
        view={view}
        resultCount={searching && !feed.loading && feed.error === null ? feed.total : null}
        onQueryChange={(q) => feed.update({ q })}
        onSortChange={(sort) => feed.update({ sort })}
        onViewChange={setView}
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

      {!feed.loading && feed.error === null && feed.items.length === 0 && (
        // Two empty states, never one. "Nothing matched" offers to clear the query; "no work
        // yet" offers to create a project. Shipping one for both strands a new user on a
        // search-reset button that does nothing.
        <div className="projects-empty" data-testid={searching ? 'projects-empty-search' : 'projects-empty-none'}>
          {searching ? (
            <>
              <p>Ничего не найдено.</p>
              <button type="button" data-testid="projects-clear-search" onClick={() => feed.update({ q: '' })}>
                Сбросить поиск
              </button>
            </>
          ) : (
            <>
              <p>Работ пока нет.</p>
              <button type="button" data-testid="projects-create" onClick={onCreateProject}>
                Создать проект
              </button>
            </>
          )}
        </div>
      )}

      {showRecent && (
        <section className="projects-section" data-testid="projects-recent">
          <h2 className="projects-section-title">Недавние проекты</h2>
          <ProjectsFeed
            items={feed.items.slice(0, RECENT_COUNT)}
            view="grid"
            onOpen={open}
            testIdPrefix="recent"
          />
        </section>
      )}

      {feed.items.length > 0 && (
        <section className="projects-section">
          {showRecent && <h2 className="projects-section-title">Все проекты</h2>}
          <ProjectsFeed items={feed.items} view={view} onOpen={open} />
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
