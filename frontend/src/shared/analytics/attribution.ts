// First-touch campaign attribution, frozen in the browser.
//
// FIRST touch, not last: the set is written once and never overwritten, so a visitor who arrives
// from a paid ad, leaves, comes back through a newsletter and registers a week later is credited
// to the ad that found them. Last-touch would credit the newsletter for an audience the ad
// bought, which is the single most expensive number to get wrong in a CAC report.
//
// It is frozen in the BROWSER because the account is created later — sometimes days later, and in
// the OAuth case two redirects away from anything the client can put in a body. Whatever the
// browser froze is what the registration carries.
import { readStored, removeStored, writeStored } from '../lib/browser'

const ATTRIBUTION_KEY = 'textery.analytics.attribution'

export const UTM_KEYS = [
  'utm_source',
  'utm_medium',
  'utm_campaign',
  'utm_content',
  'utm_term',
] as const

export type Attribution = Partial<Record<(typeof UTM_KEYS)[number], string>>

// Read once per load and cached: `captureAttribution` runs on mount and every registration reads
// it back, and re-parsing storage per read makes the "did the first touch win" question depend on
// timing rather than on the write that already happened.
let cached: Attribution | null = null

// Call once, as early in the page's life as possible. Freezes the current URL's campaign
// parameters if — and only if — nothing was frozen before.
export function captureAttribution(search: string): void {
  if (frozenAttribution() !== null) return
  const current = parseUtm(search)
  // A visit with NO campaign parameters leaves the browser open to a later first touch: writing
  // an empty set here would mean the first direct visit permanently blocks attribution for every
  // marketing link that follows, which is the common case for anyone who bookmarks the landing
  // page.
  if (Object.keys(current).length === 0) return
  cached = current
  writeStored('local', ATTRIBUTION_KEY, JSON.stringify(current))
}

// What a registration should carry. `{}` when nothing was ever frozen.
export function attributionForRegistration(): Attribution {
  return frozenAttribution() ?? {}
}

export function forgetAttribution(): void {
  cached = null
  removeStored('local', ATTRIBUTION_KEY)
}

function frozenAttribution(): Attribution | null {
  if (cached) return cached
  const stored = readStored('local', ATTRIBUTION_KEY)
  if (stored === null) return null
  // Anything unreadable is treated as "nothing was frozen" rather than repaired: the value is
  // ours, so a corrupt one means a bug or a hand-edit, and the honest recovery is to let the next
  // real campaign link become the first touch.
  const parsed = parseJson(stored)
  if (parsed === null || typeof parsed !== 'object') return null
  cached = onlyUtmStrings(parsed as Record<string, unknown>)
  return cached
}

function parseUtm(search: string): Attribution {
  // `URLSearchParams` decodes percent-escapes and `+` for us, so a multibyte campaign name
  // survives the freeze as the text it was rather than as its encoding.
  const parameters = new URLSearchParams(search)
  const found: Attribution = {}
  for (const key of UTM_KEYS) {
    const value = parameters.get(key)
    // An explicitly empty parameter (`?utm_term=`) is the same as an omitted one — a link ending
    // that way carries no term — and the backend stores both as NULL.
    if (value !== null && value !== '') found[key] = value
  }
  return found
}

function onlyUtmStrings(source: Record<string, unknown>): Attribution {
  const found: Attribution = {}
  for (const key of UTM_KEYS) {
    const value = source[key]
    if (typeof value === 'string' && value !== '') found[key] = value
  }
  return found
}

function parseJson(source: string): unknown {
  try {
    return JSON.parse(source) as unknown
  } catch {
    return null
  }
}
