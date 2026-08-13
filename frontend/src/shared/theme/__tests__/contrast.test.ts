import { describe, expect, it } from 'vitest'
import { contrastOf, darkTokens, lightTokens, resolve } from './tokenSheets'

// A dark theme assembled by eye reliably lands on grey-over-grey: the eye adapts to the page and
// stops reporting that the muted text it just dimmed is now unreadable. These measure it instead.
//
// 4.5:1 is WCAG 2.1 AA for body text. Every pair below is body text or smaller, so none of them
// gets the 3:1 large-text allowance.
const AA_NORMAL = 4.5

const SURFACES = ['--bg-page', '--bg-surface', '--bg-surface-raised', '--bg-sunken', '--bg-card']
const TEXT = ['--text-primary', '--text-secondary', '--text-muted']
const HUES = ['blue', 'coral', 'purple', 'teal']

// PAIRS THAT ALREADY FAILED BEFORE THE DARK THEME EXISTED, pinned at their measured ratios.
//
// All three are light-theme values read off the Figma file and shipped long before this story:
// `--neutral-600` as muted text, and the coral and teal type badges. They are recorded rather than
// exempted, for two reasons. Deleting the assertion would hide them; loosening the floor would
// hide the NEXT one too. Pinned to two decimals, the suite still fails if any of them gets worse,
// if a new pair joins them — and, deliberately, if one of them is FIXED, at which point the entry
// comes out and the pair rejoins the strict set.
//
// Repainting the product's light palette is not this story's work and is not a thing to attempt
// against a deadline: `--text-muted` alone is on every timestamp and caption in the app.
const LIGHT_BASELINE: Record<string, number> = {
  '--text-muted on --bg-page': 3.64,
  '--text-muted on --bg-surface': 4.15,
  '--text-muted on --bg-surface-raised': 4.15,
  '--text-muted on --bg-sunken': 3.9,
  '--text-muted on --bg-card': 4.15,
  '--chip-coral-fg on --chip-coral-bg': 2.98,
  '--chip-teal-fg on --chip-teal-bg': 3.41,
}

function measure(pairs: [string, string][], theme: 'light' | 'dark', floor: number) {
  const shortfall: Record<string, number> = {}
  for (const [fg, bg] of pairs) {
    const ratio = Number(contrastOf(fg, bg, theme).toFixed(2))
    if (ratio < floor) shortfall[`${fg} on ${bg}`] = ratio
  }
  return shortfall
}

// Every AA-floor pair in one place, so a shortfall is reported against the whole set rather than
// aborting at the first one — fixing them one red run at a time is how a palette ends up tuned
// against one surface and broken against the next.
function aaPairs(): [string, string][] {
  return [
    ...TEXT.flatMap((text): [string, string][] => SURFACES.map((surface) => [text, surface])),
    // Links, and the most-clicked text in the product.
    ['--accent', '--bg-surface'],
    ['--accent', '--bg-page'],
    ['--btn-primary-fg', '--btn-primary-bg'],
    // The four project-type badges: small text on its own tinted fill. Keeping the light `fg` over
    // a dark `bg` was the first cut of the dark sheet and gave #004ee0 on #10243a — 1.3:1.
    ...HUES.map((hue): [string, string] => [`--chip-${hue}-fg`, `--chip-${hue}-bg`]),
    // The banner triple, whose foreground and background are chosen together.
    ['--warning-fg', '--warning-bg'],
    // The footer slab — the one surface that stays dark in both themes.
    ['--text-inverse', '--bg-inverse'],
  ]
}

describe('token sheets', () => {
  // The structural rule the whole two-file split exists to make checkable. A token defined ONLY
  // under [data-theme='dark'] has no light value to fall back to: the property resolves to nothing
  // and reverts to its initial value — black text, a transparent background — which reads as a
  // rendering bug rather than as a missing token, so nobody looks for it in the token sheet.
  it('defines every dark token on the bare :root as well', () => {
    expect([...darkTokens.keys()].filter((name) => !lightTokens.has(name))).toEqual([])
  })

  // Guards the guard: these maps are parsed out of the CSS files, and a read that quietly returned
  // the wrong file would leave them empty — at which point every check above and below passes
  // vacuously. It has already happened once (see the note in tokenSheets.ts).
  it('parsed a non-trivial sheet for each layer', () => {
    expect(lightTokens.size).toBeGreaterThan(50)
    expect(darkTokens.size).toBeGreaterThan(30)
  })

  // The reverse direction is NOT an error — a token identical in both themes (radii,
  // `--text-inverse`, `--avatar-gradient`) belongs in the light sheet only. What would be an error
  // is a light token that no theme can resolve, so this checks resolvability, not presence.
  it('resolves every light token to a literal in both themes', () => {
    for (const name of lightTokens.keys()) {
      expect(() => resolve(name, 'light')).not.toThrow()
      expect(() => resolve(name, 'dark')).not.toThrow()
    }
  })
})

describe('contrast', () => {
  // The whole point of the story. No baseline, no allowance: the dark theme is new, so nothing in
  // it is inherited and every pair is expected to clear AA on the day it lands.
  it('clears AA on every dark-theme pair', () => {
    expect(measure(aaPairs(), 'dark', AA_NORMAL)).toEqual({})
  })

  it('clears AA on every light-theme pair except the pinned inherited ones', () => {
    expect(measure(aaPairs(), 'light', AA_NORMAL)).toEqual(LIGHT_BASELINE)
  })

  // The primary button is a filled control with no border, so the only thing separating it from
  // the page is its own fill. 3:1 is the WCAG AA floor for a non-text control boundary — and it is
  // exactly what `--blue-700` failed on a dark page (2.6:1), which is why `--blue-600` exists.
  it.each(['light', 'dark'] as const)(
    'separates the primary button from the page in %s',
    (theme) => {
      const pairs: [string, string][] = [
        ['--btn-primary-bg', '--bg-page'],
        ['--btn-primary-bg', '--bg-surface'],
      ]

      expect(measure(pairs, theme, 3)).toEqual({})
    },
  )
})
