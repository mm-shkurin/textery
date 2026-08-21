// Reporting an event to the backend, in a way the visitor can never notice.
//
// Every property of this module is a refusal to let analytics matter to the person using the app:
//
//   * Nothing is awaited by a caller. `report` returns void, so a screen cannot accidentally
//     block its own render on a network call that exists to count it.
//   * Every failure is swallowed. An unreachable endpoint, a 400, a 429, a CORS refusal and a
//     timeout are all the same outcome here — nothing. The one thing that is NOT swallowed is the
//     counting of it: each failure family increments a local tally a developer can read, because
//     "analytics is silently dead" is otherwise indistinguishable from "nobody visited".
//   * `keepalive` is set, which is the whole reason `fetch` is used rather than a plain request:
//     a visitor who lands and immediately closes the tab must still be counted, and a normal
//     request in an unloading document is cancelled by the browser.
//
// The occurrence key is minted PER CALL and is what makes the report idempotent server-side.
// React StrictMode double-invokes effects and genuinely sends the second request — the app's own
// `useGeneratedDocumentInit` records exactly that — so a caller cannot prevent the duplicate. It
// carries the same key, and the server collapses it.
import { API } from '../api/endpoints'
import { getAccessToken } from '../session/authSession'
import { mintUuid } from './uuid'
import { visitorIdentity } from './visitorId'

export const BROWSER_EVENTS = {
  siteVisited: 'SITE_VISITED',
  registrationStarted: 'REGISTRATION_STARTED',
  editorOpened: 'EDITOR_OPENED',
} as const

export type BrowserEvent = (typeof BROWSER_EVENTS)[keyof typeof BROWSER_EVENTS]

export type SendOutcome = 'ok' | 'refused' | 'unreachable'

// A tally, not a log. Read by tests and available in the console; deliberately not sent anywhere,
// since a reporter for the reporter is the next thing to fail silently.
const outcomes: Record<SendOutcome, number> = { ok: 0, refused: 0, unreachable: 0 }

export function sendOutcomes(): Readonly<Record<SendOutcome, number>> {
  return { ...outcomes }
}

export function resetSendOutcomes(): void {
  outcomes.ok = 0
  outcomes.refused = 0
  outcomes.unreachable = 0
}

export function report(eventName: BrowserEvent, payload?: Record<string, unknown>): void {
  // Fire-and-forget on purpose, and `void` rather than a floating promise so a rejection cannot
  // surface as an unhandled rejection in the visitor's console.
  void deliver(eventName, payload).catch(() => {
    outcomes.unreachable += 1
  })
}

async function deliver(eventName: BrowserEvent, payload?: Record<string, unknown>): Promise<void> {
  const identity = visitorIdentity()
  const response = await fetch(API.analytics.events, {
    method: 'POST',
    headers: authorizationHeaders(),
    // `keepalive` outlives the document: this is how a visitor who leaves immediately is still
    // counted (`04` §4.4). It caps the body at 64 KiB, which these events are nowhere near.
    keepalive: true,
    body: JSON.stringify({
      event_name: eventName,
      visitor_id: identity.visitorId,
      occurrence_key: mintUuid(),
      degraded: identity.degraded,
      payload: payload ?? {},
    }),
  })
  outcomes[response.ok ? 'ok' : 'refused'] += 1
}

function authorizationHeaders(): Record<string, string> {
  const token = getAccessToken()
  return {
    'Content-Type': 'application/json',
    // Sent when there IS one, so a signed-in visitor's events reach their account. Never fetched,
    // never refreshed: this route works perfectly well anonymously, and a 401 here must not become
    // a token renewal — an analytics call is not a reason to touch the session.
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}
