// `defaultProtocol: 'http'` does NOT normalize on the `setLink` path — it
// reaches only `isAllowedUri` and the linkify/autolink path, while `setLink`
// stores `attributes` verbatim (`extension-link/dist/index.js:365-376`). So a
// bare host must be prefixed here or it serializes as `<a href="example.com">`,
// a relative URL against our own origin, and is persisted that way forever.
// isAllowedUri's own protocol set (extension-link/src/link.ts:168-179). A
// leading `scheme:` whose scheme is in THIS set passes through untouched. Keyed
// on the SET, not the string shape, because `word:digits` cannot separate a
// SCHEME (`tel:79001234567`) from a dotless HOST (`localhost:3000`): only
// membership can. `javascript:` is absent, so it still reaches isAllowedUri
// unprefixed and is rejected — the passthrough must not admit it.
const ALLOWED_SCHEMES = new Set([
  'http',
  'https',
  'ftp',
  'ftps',
  'mailto',
  'tel',
  'callto',
  'sms',
  'cid',
  'xmpp',
])
const SCHEME_MATCH = /^([a-zA-Z][a-zA-Z0-9+.-]*):/

const IS_EMAIL = /^[^\s@/]+@[^\s@/]+$/
// The path class is `\S*`, deliberately: a path ends at whitespace and nowhere
// else, and `apply()` trims before calling. Enumerating its characters is what
// breaks — `\w` stays ASCII-only even under `/u` (dropping `Война_и_мир`) and
// excludes `@` (dropping `/@vsauce`). That `\w`-path mutant is what guard 4 of
// `ManualEditor.link.urlShapes.guards.test.tsx` names verbatim and exists to
// kill; guard 1 caught it too, but only incidentally — its own kill target is
// the email-branch candidate. Do not re-enumerate this class: no test forbids
// it (an enumeration passes the whole suite), only this comment does.
const HOST_SHAPE = /^[\p{L}\p{N}-]+(\.[\p{L}\p{N}-]+)*(:\d+)?([/?#]\S*)?$/u

// A href isAllowedUri always rejects (unknown ascii scheme → setLink returns
// false → apply() shows the inline alert). Its value never reaches the DOM;
// it only signals "refuse this input".
const REJECT = 'unsafe:rejected'

// Post-normalization usability screen. `HOST_SHAPE` is unrejectable by
// construction (everything it matches gets `http://` and isAllowedUri vets the
// scheme only), so an out-of-range port (`example.com:99999999999`, dead on
// `new URL()`) or an invisible/control/format char (`\p{C}` — soft hyphen
// U+00AD, U+200B, U+202E, C0 controls) would otherwise ship as a live but
// dead/deceptive link. `\p{C}` is refused; `\p{L}`/`\p{So}` (Cyrillic hosts,
// emoji paths) are not, so those stay green.
function isUsable(href: string): boolean {
  if (/\p{C}/u.test(href)) return false
  try {
    new URL(href)
    return true
  } catch {
    return false
  }
}

export function normalizeHref(url: string): string {
  const scheme = SCHEME_MATCH.exec(url)?.[1].toLowerCase()
  if (scheme && ALLOWED_SCHEMES.has(scheme)) return url

  if (HOST_SHAPE.test(url)) {
    const href = `http://${url}`
    return isUsable(href) ? href : REJECT
  }
  // A disallowed scheme (`javascript:`) reaches isAllowedUri unprefixed and is
  // rejected there.
  if (scheme) return url
  if (IS_EMAIL.test(url)) return `mailto:${url}`
  // Fallback: bare relative paths (`/docs`, `#anchor`, `?q=1`) and
  // invisible-char hosts that miss HOST_SHAPE (soft hyphen is category Cf, not
  // in the host class). None is a usable absolute URL — reject rather than link
  // a relative href against our own origin.
  return REJECT
}
