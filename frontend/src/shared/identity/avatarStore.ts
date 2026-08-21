// The avatar's BYTES, once per page — the sibling of `identityStore` and driven by it.
//
// `<img src="/api/v1/auth/me/avatar">` cannot work: the browser makes that request itself and
// attaches no `Authorization` header, because the token is in sessionStorage rather than a
// cookie. Every user would get a 401 and an empty frame. So the app fetches the bytes with the
// token and hands the <img> an object URL instead.
//
// One fetch per PAGE, not per component. Two `ProfileAvatar`s are mounted at once on the profile
// screen; a hook that fetched on mount would download the same picture twice and hold two object
// URLs for it.
//
// The URL is REVOKED whenever it stops being current — a new upload, a delete, a sign-out. It is
// deliberately NOT revoked when one avatar unmounts: the other one is still displaying it, and
// freeing it there turns the remaining header into a broken image. The store owns the lifetime
// because the store owns the value.
import { fetchAvatarBytes } from './api/avatarApi'
import type { Profile } from './api/profileWire'
import { listenerSet } from '../lib/listeners'

let currentKey: string | null = null
let url: string | null = null
// Which key the in-flight request belongs to, so a response that arrives after a newer upload is
// dropped instead of overwriting it.
let pendingKey: string | null = null
const listeners = listenerSet()

export function avatarSnapshot(): string | null {
  return url
}

export function subscribeAvatar(listener: () => void): () => void {
  return listeners.subscribe(listener)
}

function notify(): void {
  listeners.notify()
}

function release(): void {
  if (url === null) return
  URL.revokeObjectURL(url)
  url = null
  notify()
}

// Called from `identityStore` on every snapshot change. `avatarUpdatedAt` is both the "is there a
// picture" flag and the cache key: when the string changes the picture changed.
export function syncAvatar(profile: Profile | null): void {
  const nextKey = profile?.avatarUpdatedAt ?? null
  if (nextKey === currentKey) return
  currentKey = nextKey
  pendingKey = nextKey
  // Dropped BEFORE the new one is fetched, and that ordering is the point: a null profile is
  // either a sign-out or an identity being reloaded, and showing the previous account's face
  // while the next one loads is a leak, not a stale pixel.
  release()
  if (nextKey === null) return

  fetchAvatarBytes().then(
    (blob) => {
      // Superseded while in flight — the user uploaded again, or signed out. Creating a URL here
      // would leak it, because nothing else knows it exists.
      if (pendingKey !== nextKey) return
      url = URL.createObjectURL(blob)
      notify()
    },
    () => {
      // No picture on screen and no other consequence. This request goes through
      // `identityRequest`, so a failure — 404, 5xx, a timeout — never ends the session, and the
      // avatar falls back to initials rather than to an error the user cannot act on.
    },
  )
}

export function resetAvatar(): void {
  currentKey = null
  pendingKey = null
  release()
}
