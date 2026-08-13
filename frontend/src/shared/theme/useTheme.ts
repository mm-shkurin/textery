import { useSyncExternalStore } from 'react'
import { subscribeTheme, themeSnapshot } from './themeStore'
import type { Theme } from './theme'

// The third argument is the server/hydration snapshot. It is the same function as the client one
// on purpose: there is no SSR here, but `useSyncExternalStore` warns when it is omitted and the
// store's value is a plain string that is valid to read at any time.
export function useTheme(): Theme {
  return useSyncExternalStore(subscribeTheme, themeSnapshot, themeSnapshot)
}
