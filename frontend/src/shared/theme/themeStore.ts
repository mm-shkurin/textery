// ONE theme per document, subscribed to by however many components need to read it.
//
// Modelled on `identityStore.ts` for the same reason: the thing being tracked is a property of the
// DOCUMENT, not of any component, and `useState` in the menu would give every mounted menu its own
// idea of the theme while <html> carries a third. The store's job is to be the single writer of
// the attribute and to tell subscribers after it has written.
//
// This is module state on the CLIENT — the "no in-memory state" rule is about the multi-instance
// backend. Per-device on purpose: the choice is never sent anywhere, there is no field for it on
// the profile, and one is not being added for this.
import { applyTheme, currentTheme, storeTheme, type Theme } from './theme'

// Seeded from the attribute the boot script already set, NOT re-resolved. Re-resolving here would
// be a second, later answer to a question already answered before paint, and the two would differ
// exactly when the user has stored a choice — the case that matters.
let state: Theme = currentTheme()

const listeners = new Set<() => void>()

// A string, so it is referentially stable by construction. `useSyncExternalStore` re-renders on
// `Object.is` inequality; a snapshot that allocated would loop forever.
export function themeSnapshot(): Theme {
  return state
}

export function subscribeTheme(listener: () => void): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export function setTheme(next: Theme): void {
  // The attribute lands BEFORE the notify. Subscribers re-render against a document that is
  // already in the new theme, so no frame exists where a component says "тёмная" over a light page.
  applyTheme(next)
  storeTheme(next)
  if (next === state) return
  state = next
  for (const listener of [...listeners]) listener()
}

// The one write path the UI uses. It reads from `state` rather than from the attribute so that a
// stray external mutation of <html> cannot desync the two — `setTheme` re-asserts the attribute
// on every call regardless.
export function toggleTheme(): void {
  setTheme(state === 'dark' ? 'light' : 'dark')
}

// The safety net for a page whose inline boot script never ran (a CSP that forbids inline script,
// a stripped index.html). Idempotent and free when the script DID run: it re-writes the attribute
// that is already there. Called from the entry point, not from a component — a component's effect
// runs after the first paint, which is the flash this whole design exists to remove.
export function initTheme(): void {
  applyTheme(state)
}

// Tests only. Drops subscribers' cached value back to whatever the document now says, so one
// test's toggle cannot leak into the next test's default.
export function resetTheme(): void {
  state = currentTheme()
  for (const listener of [...listeners]) listener()
}
