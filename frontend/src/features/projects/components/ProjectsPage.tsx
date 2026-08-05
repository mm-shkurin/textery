import { useEffect, useState } from 'react'
import { listProjects, type ProjectSummary } from '../api/projectsApi'
import { describeFailure } from '../../../shared/api/send'
import { ProjectCard, projectKey } from './ProjectCard'
import './ProjectsPage.css'

// Same sentence `listProjects` hands `send` as its fallback. It is only reached for a failure that
// carries no text of its own — a bare `HttpError` from a 5xx, which `send` rethrows unflattened and
// which is NOT an `Error`, so reading `.message` off it would render "undefined" on the page.
const LOAD_FAILURE_FALLBACK = 'Не удалось загрузить проекты'

// The «Мои проекты» feed. Scenario 1.1 only: the cards, and nothing around them — no search, no
// sort, no view toggle, no paging control. Those arrive with their own scenarios and their own
// tests; adding the markup now would ship controls that answer to nothing.
export function ProjectsPage() {
  const [items, setItems] = useState<ProjectSummary[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    listProjects()
      .then((page) => {
        // The component unmounts mid-flight in a test teardown and in every route change; setting
        // state on the way out is a warning today and a leak the moment paging keeps a second
        // request alive.
        if (!cancelled) setItems(page.items)
      })
      // Without this the page a broken load produces is byte-identical to the page a user with no
      // projects gets, and the rejection escapes as an unhandled one on top.
      .catch((failure: unknown) => {
        // The unmount flag guards this path too, not just the resolve above: a rejection is just as
        // able to arrive after teardown as a resolution.
        if (cancelled) return
        // `describeFailure`, never `failure.message`. It is the same routing `useGeneration` uses
        // (useGeneration.ts:111), and it is what keeps the `SessionExpiredError` carve-out
        // (send.ts:62) intact HERE: an expired session keeps its own "Сессия истекла. Войдите
        // снова." rather than being retitled with this screen's fallback and blamed on the feed.
        // Rendering that sentence inline is this codebase's whole sign-out affordance today —
        // `ManualEditor` shows it in exactly the same banner (saveFailureMessages.ts:33) and no
        // route in the app redirects on it. There is no polling loop or retry timer here to stop,
        // which is the only other thing the generation hook's branch does with the type.
        setError(describeFailure(failure, LOAD_FAILURE_FALLBACK))
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="projects-page" data-testid="projects-page">
      {error !== null && (
        <p className="projects-error" data-testid="projects-error">
          {error}
        </p>
      )}
      {items.map((project) => (
        // Keyed on `projectKey`, never on id alone — see the comment on that function.
        <ProjectCard key={projectKey(project)} project={project} />
      ))}
    </div>
  )
}
