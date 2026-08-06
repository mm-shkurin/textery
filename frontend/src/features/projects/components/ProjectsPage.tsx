import { useEffect, useState } from 'react'
import { listProjects, LOAD_FAILURE_FALLBACK, type ProjectSummary } from '../api/projectsApi'
import { describeFailure } from '../../../shared/api/send'
import { RequestTimeoutError } from '../../../shared/api/httpClient'
import { ProjectCard, projectKey } from './ProjectCard'
import './ProjectsPage.css'

// Failure types that reach this screen carrying ENGLISH text of their own. `send.ts:93` re-throws
// `RequestTimeoutError` by identity so the autosave retry policy can still classify it, and its
// message is the transport-layer literal `httpClient.ts:70-75` hardcodes ("Request timed out") —
// which `describeFailure`'s last line then prefers over the caller's fallback, painting English on
// a Russian-only screen on the failure a real user hits most.
//
// A TYPE LIST, deliberately, rather than "stop preferring `Error.message` in this catch": that
// wording would also swallow `SessionExpiredError`, whose own «Сессия истекла. Войдите снова.» is
// this codebase's entire sign-out affordance here (no route redirects on it), retitling an expired
// session as a generic feed error with a retry that can never succeed. Anything not listed keeps
// `describeFailure`'s routing unchanged, including the bare-object-literal `HttpError` a 5xx
// arrives as.
//
// NOT fixed at `send.ts:52`: that line is shared by `useDocumentInit`, `useGeneration`, the
// ManualEditor save path and the auth forms, and its non-`HttpError` arm has no characterization
// test anywhere — an app-wide wording change there would go unnoticed by the suite.
const OPAQUE_TRANSPORT_FAILURES = [RequestTimeoutError]

function describeLoadFailure(failure: unknown): string {
  if (OPAQUE_TRANSPORT_FAILURES.some((type) => failure instanceof type)) {
    return LOAD_FAILURE_FALLBACK
  }
  return describeFailure(failure, LOAD_FAILURE_FALLBACK)
}

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
        // `describeFailure`, never `failure.message`: a 5xx arrives here as a bare `HttpError`
        // object literal, which is NOT an `Error`, so `.message` would paint "undefined" on the
        // page. It is the same routing `useGeneration` uses
        // (useGeneration.ts:111), and it is what keeps the `SessionExpiredError` carve-out
        // (send.ts:62) intact HERE: an expired session keeps its own "Сессия истекла. Войдите
        // снова." rather than being retitled with this screen's fallback and blamed on the feed.
        // Rendering that sentence inline is this codebase's whole sign-out affordance today —
        // `ManualEditor` shows it in exactly the same banner (saveFailureMessages.ts:33) and no
        // route in the app redirects on it. There is no polling loop or retry timer here to stop,
        // which is the only other thing the generation hook's branch does with the type.
        setError(describeLoadFailure(failure))
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="projects-page" data-testid="projects-page">
      {error !== null && (
        // `role="alert"` sits on the element that carries the sentence, not on a wrapper or an
        // always-present empty region: an assistive-technology user hears the failure only if the
        // words are inside the live region at the moment it appears. The guard above stays for the
        // same reason `RegisterForm.tsx:65` only renders its role in the error state — an assertive
        // region mounted at first paint announces on load, before anything has gone wrong.
        <p className="projects-error" data-testid="projects-error" role="alert">
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
