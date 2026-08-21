import { useCallback } from 'react'
import { useProjectsFeed } from '../hooks/useProjectsFeed'
import { useProjectView } from '../hooks/useProjectView'
import { ProjectsNavbar } from './ProjectsNavbar'
import { ProjectsToolbar } from './ProjectsToolbar'
import { ProjectsPageHeader } from './ProjectsPageHeader'
import { ProjectsFeedSections } from './ProjectsFeedSections'
import { ProjectsPager } from './ProjectsPager'
import { useRetryGeneration } from '../hooks/useRetryGeneration'
import type { ProjectSummary } from '../api/projectsApi'
import './ProjectsPage.module.css'
import projectsScreenStyles from './ProjectsScreen.module.css'
import { QueryBoundary } from '../../../shared/query/QueryBoundary'
import { SiteFooter } from '../../../shared/components/SiteFooter'

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

function ProjectsPageScreen({
  onOpenDocument,
  onCreateProject,
  onBack,
  onLogoutClick,
}: ProjectsPageProps = {}) {
  const feed = useProjectsFeed()
  const [view, setView] = useProjectView()
  const retry = useRetryGeneration(feed.markRetried)

  const searching = feed.q.trim() !== ''

  // Stable across renders so the memoized cards are not invalidated by the page re-rendering
  // for an unrelated reason — a keystroke in the toolbar's search box, most of all.
  const open = useCallback(
    (project: ProjectSummary) => {
      // Only a document has an editor to open. A generation card is a record of work that never
      // became one, and its id comes from the other table entirely.
      if (project.kind === 'document') onOpenDocument?.(project.id, project.documentType)
    },
    [onOpenDocument],
  )

  return (
    // The shell paints the page. Frame 484:1104 is drawn on WHITE, not on the product's blue
    // wash: the cards are white too, and the design separates them from the page by their
    // hairline rather than by a tint. On `--bg-page` the whole feed read as one blue field with
    // white patches on it.
    <div className={projectsScreenStyles['projects-shell']} data-testid="projects-screen">
      <div className={projectsScreenStyles['projects-screen']}>
        <ProjectsNavbar onLogoutClick={onLogoutClick} />

        <ProjectsPageHeader onBack={onBack} />

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

        <ProjectsFeedSections
          feed={feed}
          view={view}
          searching={searching}
          retry={retry}
          onOpen={open}
          onCreateProject={onCreateProject}
        />

        <ProjectsPager
          page={feed.page}
          limit={feed.limit}
          total={feed.total}
          onPage={(page) => feed.update({ page })}
        />
      </div>

      {/* The frame ends the screen on the pale footer strip (node 788:5094, y=16279) — the same
          copyright and links the landing's slab carries, without its four columns. */}
      <SiteFooter variant="strip" />
    </div>
  )
}

/**
 * The screen, with the data cache it reads through.
 *
 * Wrapped here rather than only at the app root so the page can be rendered on its own — by a
 * test, by a future route — without silently requiring an ancestor it never names. The boundary
 * carries the same client either way, so nesting changes nothing at runtime.
 */
export function ProjectsPage(props: Parameters<typeof ProjectsPageScreen>[0]) {
  return (
    <QueryBoundary>
      <ProjectsPageScreen {...props} />
    </QueryBoundary>
  )
}
