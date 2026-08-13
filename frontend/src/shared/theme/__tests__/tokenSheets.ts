// The token sheets as DATA, so the contrast test measures the values that SHIP rather than a table
// of numbers copied beside them. jsdom computes no colours for a stylesheet it never loaded, which
// rules out reading them back off the document; parsing the source is what is left.
//
// Read off DISK, and both obvious alternatives are traps that fail SILENTLY rather than loudly:
//
//  - `import css from './x.css?raw'` returns an EMPTY STRING under vitest, which replaces CSS
//    imports with empty modules unless `test.css` is switched on for the whole suite.
//  - `readFileSync(new URL('./x.css', import.meta.url))` looks like a path but is not one: Vite
//    rewrites `new URL(<literal>, import.meta.url)` into an asset reference at transform time.
//
// Both were tried here, in that order. Each produced empty token maps, and empty maps make the
// structural tests pass VACUOUSLY while the contrast tests throw "token is not defined" — hence
// the sheet-size guard in contrast.test.ts, which exists purely to catch a third variant of this.
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const stylesDir = join(dirname(fileURLToPath(import.meta.url)), '..', '..', '..', 'styles')

function sheet(name: string): string {
  // Comments stripped first: the sheets quote hex literals inside prose ("#004ee0 on #10243a
  // measures 1.3:1"), and a declaration regex over the raw text would read those as tokens.
  return readFileSync(join(stylesDir, name), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '')
}

function declarationsIn(css: string): Map<string, string> {
  const found = new Map<string, string>()
  for (const [, name, value] of css.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) {
    found.set(name, value.trim())
  }
  return found
}

export const paletteTokens = declarationsIn(sheet('palette.css'))
export const lightTokens = declarationsIn(sheet('tokens-light.css'))
export const darkTokens = declarationsIn(sheet('tokens-dark.css'))

// Follows `var(--a)` chains to a literal. `depth` bounds a cycle: a token pair that referenced
// each other would otherwise hang the run rather than fail it.
export function resolve(name: string, theme: 'light' | 'dark', depth = 0): string {
  if (depth > 12) throw new Error(`Cyclic token reference at ${name}`)
  const layers =
    theme === 'dark' ? [darkTokens, lightTokens, paletteTokens] : [lightTokens, paletteTokens]
  const value = layers.map((layer) => layer.get(name)).find((found) => found !== undefined)
  if (value === undefined) throw new Error(`Token ${name} is not defined in the ${theme} theme`)
  const reference = /^var\((--[\w-]+)\)$/.exec(value)
  return reference === null ? value : resolve(reference[1], theme, depth + 1)
}

// sRGB relative luminance, WCAG 2.1 §Relative luminance. Opaque colours only — every pair this
// suite measures is a solid text colour on a solid background, and compositing an alpha layer
// would need the stack underneath it, which a stylesheet does not record.
function luminance(color: string): number {
  const hex = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(color.trim())
  if (hex === null) throw new Error(`Not an opaque hex colour: ${color}`)
  const digits = hex[1].length === 3 ? [...hex[1]].map((d) => d + d).join('') : hex[1]
  const channels = [0, 2, 4].map((at) => Number.parseInt(digits.slice(at, at + 2), 16) / 255)
  const linear = channels.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4))
  return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
}

export function contrastRatio(foreground: string, background: string): number {
  const [lighter, darker] = [luminance(foreground), luminance(background)].sort((a, b) => b - a)
  return (lighter + 0.05) / (darker + 0.05)
}

export function contrastOf(fgToken: string, bgToken: string, theme: 'light' | 'dark'): number {
  return contrastRatio(resolve(fgToken, theme), resolve(bgToken, theme))
}
