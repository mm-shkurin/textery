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

// A different question from isTransientFailure ("can waiting heal this?"): did the failure leave the
// SERVER's content unknown? The dirty guard's memory ("the server holds this text") is only safe to
// keep across a failure that provably did not land, so the two questions do not share an answer.
//
// Unknown is the DEFAULT across the whole 5xx range, not an enumeration: a server that had the
// request in hand can fail on either side of the commit, and a 500 fires from a post-commit hook as
// readily as from a rejected transaction. 503 is the sole carve-out — it is the only 5xx that ANSWERS
// the question ("unavailable, I did not take your write"). Below 500 nothing was accepted, and a
// rejection that is not an HttpError at all (a session expiry thrown before the request goes out)
// never reached a server either.
//
// Measured 2026-07-28: the 503 carve-out is a claim about the INGRESS, not the application, and the
// ingress is a CHAIN — every hop between the browser and the origin, not just the one conf below.
//
//   - the origin: `backend/adapters/rest/src/error_handling/exception_handlers.py:64-77` returns 500
//     and it is the only 5xx emitted. No handler returns 503 (verified: no `503` in `backend/`).
//     Unpinned by any test — owed to the backend session.
//   - the container nginx, `infra/docker/nginx/frontend.conf`: carries nothing that can answer 503,
//     and this is the one hop with a GATE — `frontend/scripts/check-nginx-503.mjs`
//     (`npm run check:ingress`, a CI step) fails the build on any directive that could.
//   - everything in front of that — a TLS terminator, WAF, rate limiter, the host/prod-copy reverse
//     proxy: **no IaC source in this repo, therefore no gate.** Only the note in
//     `infra/architecture.md` under Deploy notes, which also spells out the exit for a hop with no
//     config file at all: drop this carve-out rather than pretend it can be scanned.
//   - and two paths that BYPASS the gated hop, so its scan never applies: the Vite dev proxy
//     (`frontend/vite.config.ts`) and the published backend port in `infra/docker-compose.yml`
//     reach the origin without traversing that conf. Neither emits 503 today.
//
// The carve-out is safe while no component in that chain emits 503 AFTER taking a write.
export function mayHaveLandedServerSide(error: unknown): boolean {
  return isTransientFailure(error) && !(isHttpError(error) && error.status === 503)
}
