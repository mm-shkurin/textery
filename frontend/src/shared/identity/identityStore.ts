// ONE identity per page, not one per component.
//
// After story 13 the header shows the account on every authenticated screen, and it is mounted
// more than once at a time (the navbar's menu and, on the profile screen, the identity card read
// the same thing). A hook that fetched on mount would issue a `GET /me` per mount and a fresh one
// on every in-app navigation — several requests for one unchanging fact, on what this story makes
// the product's highest-rate endpoint.
//
// So the snapshot lives outside React, exactly like `authSession`, and components subscribe to it
// with `useSyncExternalStore`. The store is module state ON THE CLIENT — the "no in-memory state"
// rule is about the multi-instance backend, and this is a per-tab cache of a per-tab session.
//
// It is INVALIDATED on every session change. Signing out and back in as somebody else keeps
// `isAuthenticated` at `true` throughout — only the identity changes — so a cache keyed on
// "authenticated" alone would show the previous account's name and address to the new one.
import { getAccessToken, subscribeAuthSession } from '../../features/auth/utils/authSession'
import { fetchProfile, type Profile } from './api/profileApi'
import { resetAvatar, syncAvatar } from './avatarStore'

export type IdentityState =
  // 'idle' is never rendered: the first subscriber turns it into 'loading'. It exists so a
  // re-subscription after invalidation can tell "nothing asked yet" from "asked and failed".
  | { status: 'idle'; profile: null }
  | { status: 'loading'; profile: null }
  | { status: 'ready'; profile: Profile }
  // The request failed and the retries are spent. NOT "the session is over" — see
  // identityRequest.ts. The UI shows a visibly degraded identity and keeps working.
  | { status: 'failed'; profile: null }

const IDLE: IdentityState = { status: 'idle', profile: null }

let state: IdentityState = IDLE
let inFlight = false
let lastToken: string | null = null
const listeners = new Set<() => void>()

// Referentially STABLE between changes: `useSyncExternalStore` re-renders on `Object.is`
// inequality, so returning a fresh object per read would loop forever.
export function identitySnapshot(): IdentityState {
  return state
}

export function subscribeIdentity(listener: () => void): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

function setState(next: IdentityState): void {
  state = next
  // The avatar's bytes hang off the same snapshot, so they are synced HERE rather than by a
  // component effect: every path that changes the identity — the boot fetch, a rename, an upload,
  // a session change — is a path that may change the picture, and none of them should have to
  // remember to say so.
  syncAvatar(next.profile)
  for (const listener of [...listeners]) listener()
}

function load(): void {
  inFlight = true
  setState({ status: 'loading', profile: null })
  fetchProfile()
    .then(
      (profile) => setState({ status: 'ready', profile }),
      // Every failure mode lands here — 5xx, a timeout, a 401 whose renewal failed — and NONE of
      // them touches the stored session.
      () => setState({ status: 'failed', profile: null }),
    )
    .finally(() => {
      inFlight = false
      // The fetch may have renewed the access token on its own 401. Recording it here is what
      // stops that renewal from looking like a session change and re-triggering this load.
      lastToken = getAccessToken()
    })
}

// Called from every consumer's mount effect. The second and third callers are no-ops, which is
// the whole point.
export function ensureIdentityLoaded(): void {
  if (state.status !== 'idle' || inFlight) return
  lastToken = getAccessToken()
  load()
}

// The «Повторить» button. Unlike `ensureIdentityLoaded` it re-asks from a settled failed state.
export function reloadIdentity(): void {
  if (inFlight) return
  lastToken = getAccessToken()
  load()
}

// The PATCH response IS the new snapshot — the full profile, normalized. Applying it here is what
// makes the header update without a reload and without a second GET.
export function applyProfile(profile: Profile): void {
  lastToken = getAccessToken()
  setState({ status: 'ready', profile })
}

export function resetIdentity(): void {
  inFlight = false
  resetAvatar()
  lastToken = getAccessToken()
  setState(IDLE)
}

subscribeAuthSession(() => {
  const token = getAccessToken()
  if (token === lastToken) return
  lastToken = token
  // Our own renewal, mid-fetch — not a new session. Invalidating here would abandon the request
  // that is about to answer and start another one behind it.
  if (inFlight) return
  setState(IDLE)
  // Refetch only if somebody is looking and there is a session to ask about. A signed-out tab has
  // no identity to show and every header that displayed one has unmounted.
  if (listeners.size > 0 && token !== null) load()
})
