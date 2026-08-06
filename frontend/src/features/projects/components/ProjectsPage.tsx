import { useEffect, useState } from 'react'
import {
  listProjects,
  LOAD_FAILURE_FALLBACK,
  MISSING_UPDATED_AT_MESSAGE,
  type ProjectSummary,
} from '../api/projectsApi'
import { describeFailure } from '../../../shared/api/send'
import { isHttpError } from '../../../shared/api/httpClient'
import { SessionExpiredError } from '../../auth/api/authorizedRequest'
import { ProjectCard, projectKey } from './ProjectCard'
import './ProjectsPage.css'

// AN ALLOW-LIST, and it had to become one. The previous shape here was a deny-list of transport
// types (`OPAQUE_TRANSPORT_FAILURES = [RequestTimeoutError]`) whose messages are English; it could
// not be extended to cover the failure a real user hits most. A dropped connection, a failed DNS
// lookup or an offline device makes `fetch` reject with a bare `TypeError('Failed to fetch')`,
// which matches none of `send.ts`'s carve-outs and falls to `send.ts:96` —
// `throw new Error(describeFailure(error, fallback))`. The TYPE IS DESTROYED one layer above this
// screen and only the English message survives, so there is nothing left for a deny-list to name.
//
// Inverted, the question stops being "which failures are opaque?" (an open set the transport keeps
// growing) and becomes "whose text is this, and is it already addressed to this user?" — a closed
// set, because only three things author text that belongs on a Russian-only screen:
//
//   1. the SERVER, via an `HttpError` — a 4xx's `detail`/`message` is a decided answer written for
//      the user, and a bodyless 5xx still contributes its `(HTTP 500)` suffix. Matched with
//      `isHttpError`, never `instanceof`: `HttpError` is a bare object literal
//      (`httpClient.ts:141`) and is not an `Error` at all, so a type-only allow-list would collapse
//      both of those into the generic sentence below.
//   2. `SessionExpiredError`, which `send.ts:62` re-throws BY IDENTITY. Its «Сессия истекла.
//      Войдите снова.» is this codebase's entire sign-out affordance here — no route redirects on
//      it — so retitling it as a feed failure would offer a retry that can never succeed.
//   3. THIS FEATURE'S OWN contract guards, which reach the catch flattened to a plain `Error` and
//      are therefore indistinguishable from `Failed to fetch` BY TYPE. They are matched by message
//      identity against the constants that authored them. A guard added later and not listed here
//      degrades to the generic sentence rather than leaking — the safe direction.
//
// Everything else is transport noise in a language the user did not ask for.
//
// NOT fixed at `send.ts:52`: that line is shared by `useDocumentInit`, `useGeneration`, the
// ManualEditor save path and the auth forms, and its non-`HttpError` arm has no characterization
// test anywhere — an app-wide wording change there would go unnoticed by the suite.
const FEED_AUTHORED_MESSAGES: string[] = [MISSING_UPDATED_AT_MESSAGE]

function describeLoadFailure(failure: unknown): string {
  if (isHttpError(failure) || failure instanceof SessionExpiredError) {
    return describeFailure(failure, LOAD_FAILURE_FALLBACK)
  }
  if (failure instanceof Error && FEED_AUTHORED_MESSAGES.includes(failure.message)) {
    return failure.message
  }
  return LOAD_FAILURE_FALLBACK
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
