import { useSyncExternalStore } from 'react'
import { subscribeAuthSession } from '../utils/authSession'
import { currentAccountEmail } from '../utils/accountEmail'

// The sibling of `useAuthSession`, and for the same reason: the token lives outside React, so a
// value read during render goes deaf the moment something non-React replaces it. Signing out and
// back in as somebody else keeps `isAuthenticated` at `true` throughout — only the address
// changes — so a component subscribed to the boolean alone would keep printing the previous
// account's email until an unrelated re-render happened to correct it.
//
// The snapshot is a string (or null), which `Object.is` compares by value, so re-reads that
// decode the same token are stable and cannot loop.
export function useAccountEmail(): string | null {
  return useSyncExternalStore(subscribeAuthSession, currentAccountEmail, currentAccountEmail)
}
