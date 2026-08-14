// The theme's vocabulary and its four primitive operations. No React, no module state — this file
// is the piece that `themeStore.ts` and the inline boot script in `index.html` must agree on.
//
// THE DUPLICATION IS DELIBERATE AND BOUNDED. `index.html` re-implements `resolveInitialTheme` in
// four lines of classic script because it has to run BEFORE the first paint, and a module import
// cannot: `<script type="module">` is deferred by definition, so the theme would land after the
// browser has already painted a light page. The duplicated logic is pinned by
// `__tests__/theme.test.tsx`, which extracts the real script out of the real `index.html` and
// executes it — the two cannot drift without a red test.

export type Theme = 'light' | 'dark'

// Namespaced: `localStorage` is shared per origin, and `theme` unqualified is the single most
// likely key for a future widget or embed to collide with.
export const THEME_STORAGE_KEY = 'textery.theme'
export const THEME_ATTRIBUTE = 'data-theme'

function isTheme(value: unknown): value is Theme {
  return value === 'light' || value === 'dark'
}

// Returns null for "no stored choice" AND for a stored value we do not recognise. The second case
// is not paranoia: the key is user-writable from a devtools console and survives a deploy that
// renames a theme, and an unvalidated read would put `data-theme="sepia"` on <html>, which matches
// no block and silently resolves every token to its light value while claiming otherwise.
export function readStoredTheme(): Theme | null {
  try {
    const raw = localStorage.getItem(THEME_STORAGE_KEY)
    return isTheme(raw) ? raw : null
  } catch {
    // Safari in private mode throws on `localStorage` access rather than returning null. A theme
    // that cannot be REMEMBERED must still be usable, so this degrades to "no stored choice".
    return null
  }
}

export function storeTheme(theme: Theme): void {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme)
  } catch {
    // Same as above, plus a full quota. The switch already happened on screen; losing the record
    // costs the user one extra click next visit and must not throw out of a click handler.
  }
}

// "Follow the OS" is the ABSENCE of a stored choice, not a third value written into storage.
// Modelling it as a stored `'system'` would need the inline boot script in `index.html` to learn a
// third case, and that script is duplicated logic pinned by `theme.test.tsx` — the cheapest correct
// change is the one that leaves it alone. Removing the key is exactly what `resolveInitialTheme`
// already reads as "ask the OS".
export function clearStoredTheme(): void {
  try {
    localStorage.removeItem(THEME_STORAGE_KEY)
  } catch {
    // Same private-mode throw the writer guards against.
  }
}

// What the SWITCH shows as selected, which is a different question from what the page is painted
// in: an OS-dark visitor on 'system' is looking at a dark page, and both «Системная» and «Тёмная»
// would be truthful answers to "what theme is this" — only one of them is the choice they made.
export type ThemePreference = 'system' | Theme

export function readStoredPreference(): ThemePreference {
  return readStoredTheme() ?? 'system'
}

export function systemTheme(): Theme {
  // jsdom implements no `matchMedia` at all, and neither do a few embedded webviews. Guarding the
  // FUNCTION rather than the result is what keeps this from throwing in the test environment.
  if (typeof window.matchMedia !== 'function') return 'light'
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

// The precedence the whole feature rests on: an explicit choice, then the OS, then light.
// The stored choice comes FIRST and unconditionally — a user on a dark-set OS who picked light
// picked light, and re-deciding for them each load is the bug that makes a switch feel broken.
export function resolveInitialTheme(): Theme {
  return readStoredTheme() ?? systemTheme()
}

export function applyTheme(theme: Theme): void {
  document.documentElement.setAttribute(THEME_ATTRIBUTE, theme)
}

// What is on <html> right now, which in the browser is whatever the boot script decided. Falls
// back to resolving from scratch for the two callers that have no boot script: a unit test
// rendering a component in isolation, and a page whose inline script was stripped by a CSP.
export function currentTheme(): Theme {
  const attribute = document.documentElement.getAttribute(THEME_ATTRIBUTE)
  return isTheme(attribute) ? attribute : resolveInitialTheme()
}
