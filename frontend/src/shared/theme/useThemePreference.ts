import { useSyncExternalStore } from 'react'
import { preferenceSnapshot, subscribeTheme } from './themeStore'
import type { ThemePreference } from './theme'

// The switch's own reading of the store. Separate from `useTheme` because the two answer different
// questions — `useTheme` is what the page is painted in, this is what the user chose — and a
// component that highlighted a segment from the painted theme would never be able to show
// «Системная» as selected at all.
export function useThemePreference(): ThemePreference {
  return useSyncExternalStore(subscribeTheme, preferenceSnapshot, preferenceSnapshot)
}
