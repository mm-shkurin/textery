// The browser's own identity, and the one place that decides what it is.
//
// A UUID minted on the first visit and kept in `localStorage`, so a returning browser is the same
// visitor and a funnel can span the days between "read the landing page" and "registered". It is
// NOT an account id and never becomes one: the published contract says in as many words that the
// server never infers a user from it and that no security, billing or entitlement decision may
// key on it. Treat it as a join key that anybody can forge, because anybody can.
//
// Storage can fail, and this module's whole shape follows from HOW it fails: Safari's private
// mode throws on `setItem`, an embedded webview may have storage disabled entirely, and a user
// can simply block it. None of those may stop a page from loading. So every read is guarded, a
// browser that cannot store gets a per-load identity instead, and the fact that it could not
// store is REPORTED (`degraded`) rather than hidden — two loads from such a browser are two
// visitors, and analytics that cannot tell that apart from two people is analytics that lies.
import { readStored, removeStored, writeStored } from '../lib/browser'
import { mintUuid } from './uuid'

const VISITOR_ID_KEY = 'textery.analytics.visitorId'

// A canonical v4 UUID, lower case. Anything else in storage is replaced rather than reused: the
// column is native `uuid` and a value the server cannot parse is an event refused on every send,
// forever, for that browser — a silent permanent outage of one visitor's analytics.
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

export interface VisitorIdentity {
  visitorId: string
  // True when the id could not be persisted, so it lives only for this page load.
  degraded: boolean
}

let cached: VisitorIdentity | null = null

export function visitorIdentity(): VisitorIdentity {
  // Cached per page load so a browser that cannot store keeps ONE identity across the events of a
  // single load — without this, `SITE_VISITED` and `REGISTRATION_STARTED` from the same visit
  // would arrive as two different visitors and every degraded session would read as a bounce.
  if (cached) return cached
  cached = resolveIdentity()
  return cached
}

export function visitorId(): string {
  return visitorIdentity().visitorId
}

// Called when the account is deleted: the identity and everything keyed to it goes with it.
export function forgetVisitor(): void {
  cached = null
  removeStored('local', VISITOR_ID_KEY)
}

function resolveIdentity(): VisitorIdentity {
  const stored = readStored('local', VISITOR_ID_KEY)
  if (typeof stored === 'string' && UUID_PATTERN.test(stored)) {
    return { visitorId: stored.toLowerCase(), degraded: false }
  }
  const minted = mintUuid()
  // `writeStored` reports whether the value survived, which is exactly the degraded flag: it
  // guards the property ACCESS too, because reading `localStorage` itself raises a SecurityError
  // when cookies are blocked, not only writing to it.
  const persisted = writeStored('local', VISITOR_ID_KEY, minted)
  return { visitorId: minted, degraded: !persisted }
}
