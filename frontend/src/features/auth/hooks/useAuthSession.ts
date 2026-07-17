import { useSyncExternalStore } from 'react'
import { getAccessToken, subscribeAuthSession } from '../utils/authSession'

// Whether a session exists, as a value React actually re-renders on.
//
// Calling `isAuthenticated()` during render reads the truth at that instant and then goes deaf:
// when the token is dropped by something outside React — a refresh that failed mid-poll — the
// screen keeps showing an authenticated app until an unrelated state change happens to
// re-render it. `useSyncExternalStore` closes that gap, so an expiring session collapses the UI
// by itself instead of waiting for the user to click something that no longer works.
//
// The snapshot is a boolean, not the token: returning the token would be a needless way to leak
// it into component props, and a boolean also keeps the snapshot referentially stable across
// reads, which is what `useSyncExternalStore` requires to avoid an infinite re-render loop.
function hasSession(): boolean {
  return Boolean(getAccessToken())
}

export function useAuthSession(): boolean {
  return useSyncExternalStore(subscribeAuthSession, hasSession, hasSession)
}
