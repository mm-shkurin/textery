// What a failed feed load tells the user. Pure and React-free — `ProjectsPage`'s catch consumes it,
// the same way `useDocumentSave` consumes `saveFailureMessages`. It lives beside the constants it
// routes over: both `LOAD_FAILURE_FALLBACK` and `MISSING_UPDATED_AT_MESSAGE` are authored in
// `projectsApi.ts`, and the component was importing the latter for no reason other than to fill the
// allow-list below.
import {
  INVALID_PAGE_MESSAGE,
  LOAD_FAILURE_FALLBACK,
  MISSING_UPDATED_AT_MESSAGE,
} from './projectsApi'
import { describeFailure } from '../../../shared/api/send'
import { isHttpError } from '../../../shared/api/httpClient'
import { SessionExpiredError } from '../../auth/api/authorizedRequest'

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
//
// `readonly` so the fail-closed direction cannot be widened at runtime: an allow-list that another
// module can `push` onto is an allow-list that can be made to leak the English text arm 3 exists to
// keep off this screen.
const FEED_AUTHORED_MESSAGES: readonly string[] = [
  MISSING_UPDATED_AT_MESSAGE,
  INVALID_PAGE_MESSAGE,
]

export function describeLoadFailure(failure: unknown): string {
  if (isHttpError(failure) || failure instanceof SessionExpiredError) {
    return describeFailure(failure, LOAD_FAILURE_FALLBACK)
  }
  if (failure instanceof Error && FEED_AUTHORED_MESSAGES.includes(failure.message)) {
    return failure.message
  }
  return LOAD_FAILURE_FALLBACK
}
