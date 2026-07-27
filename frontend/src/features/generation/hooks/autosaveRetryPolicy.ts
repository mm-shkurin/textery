import { RequestTimeoutError, isHttpError } from '../../../shared/api/httpClient'

// The autosave retry policy (H9.3): which failures a backoff can heal, the attempt ceiling, and the
// gap between attempts. Pure and React-free — the save state machine in useDocumentSave consumes it.

// A TRANSIENT autosave failure — a request timeout or a 5xx — is the one kind a backoff can heal, so
// it re-fires ITSELF on a capped schedule up to this many total attempts (initial + retries) before
// giving up and surfacing the banner. Exported so the test asserts one definition of the ceiling,
// never a drifting inline literal (mirrors INVALID_VERSION_MESSAGE).
export const MAX_AUTOSAVE_ATTEMPTS = 4

// Capped exponential backoff between attempts: 1s, 2s, 4s… ceilinged at 8s so a long outage does not
// stretch a single retry gap to minutes. `attempt` is the 1-based number of the attempt that just
// failed; the whole schedule for MAX_AUTOSAVE_ATTEMPTS stays well inside the tests' RETRY_WINDOW_MS.
const RETRY_BASE_MS = 1000
const RETRY_MAX_MS = 8000
export function backoffDelay(attempt: number): number {
  return Math.min(RETRY_BASE_MS * 2 ** (attempt - 1), RETRY_MAX_MS)
}

// Only a timeout or a 5xx is worth retrying: the request may recover on its own. A session expiry
// (signed out), a version conflict (someone else's write landed), or any 4xx cannot be healed by
// waiting — retrying only burns the schedule against a request that will fail identically.
export function isTransientFailure(error: unknown): boolean {
  if (error instanceof RequestTimeoutError) return true
  return isHttpError(error) && error.status >= 500
}
