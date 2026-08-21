// What a failed feed load tells the user. Pure and React-free — `ProjectsPage`'s catch consumes it,
// the same way `useDocumentSave` consumes `saveFailureMessages`. It lives beside the constants it
// routes over: both `LOAD_FAILURE_FALLBACK` and `MISSING_UPDATED_AT_MESSAGE` are authored in
// `projectsApi.ts`, and the component was importing the latter for no reason other than to fill the
// allow-list below.
//
// The RULE — session-expiry keeps its own text, the server's words win, this feature's own guards
// are matched by message identity, everything else is transport noise — moved to
// `shared/api/failureText.ts` when the document save turned out to be answering it too. What stays
// here is what is genuinely this screen's: which sentence to fall back to, and which messages the
// feed itself authored.
import {
  INVALID_PAGE_MESSAGE,
  LOAD_FAILURE_FALLBACK,
  MISSING_UPDATED_AT_MESSAGE,
} from './projectsApi'
import { describeOperationFailure } from '../../../shared/api/failureText'

// The guards `projectsApi` raises. They reach a catch flattened to a plain `Error`, so they are
// indistinguishable from `Failed to fetch` by type and can only be matched by identity.
const FEED_AUTHORED_MESSAGES: readonly string[] = [MISSING_UPDATED_AT_MESSAGE, INVALID_PAGE_MESSAGE]

export function describeLoadFailure(failure: unknown): string {
  return describeOperationFailure(failure, LOAD_FAILURE_FALLBACK, {
    authored: FEED_AUTHORED_MESSAGES,
  })
}
