import { useEffect, useSyncExternalStore } from 'react'
import { ensureIdentityLoaded, identitySnapshot, subscribeIdentity } from './identityStore'
import type { IdentityState } from './identityStore'

// The account this tab is signed in as, as a value React re-renders on.
//
// The fetch is kicked off from an EFFECT, not from the render body: a render-phase request fires
// again on every re-render and on React 18's double-invoked development render. The store
// de-duplicates it anyway, so the effect is the belt and the store is the braces.
export function useIdentity(): IdentityState {
  const state = useSyncExternalStore(subscribeIdentity, identitySnapshot, identitySnapshot)

  useEffect(() => {
    ensureIdentityLoaded()
  }, [])

  return state
}
