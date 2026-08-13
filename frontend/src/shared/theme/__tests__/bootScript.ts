// `?raw` here, but `node:fs` in tokenSheets.ts — the two are not inconsistent. vitest replaces
// CSS imports with empty modules, so `?raw` on a stylesheet silently yields '', which is why the
// token sheets are read off disk. HTML is not intercepted, so `?raw` works, and it is the better
// form when available: it goes through the same transform pipeline the app uses and so cannot be
// pointed at a stale path. The failure mode if it ever DOES yield '' is loud — the assertion below
// throws rather than letting an empty script pass as a passing test.
import indexHtml from '../../../../index.html?raw'

// The theme boot script, out of the REAL index.html, as executable source.
//
// This exists so the tests exercise the code that actually ships. Asserting against
// `resolveInitialTheme()` from theme.ts instead would test a faithful copy of the boot logic while
// the shipped copy sat in an HTML file no test ever loaded — precisely the gap that lets the two
// drift. A storage-key rename in one place and not the other must turn a test red.

// The first ATTRIBUTE-LESS <script> in the document. The only other script tag is the module entry
// (`<script type="module" src="/src/main.tsx">`), which this pattern cannot match — if that ever
// stops being true the extraction is wrong, so the count is asserted rather than assumed.
const matches = [...indexHtml.matchAll(/<script>([\s\S]*?)<\/script>/g)]

if (matches.length !== 1) {
  throw new Error(
    `Expected exactly one inline <script> in index.html, found ${matches.length}. ` +
      'The theme boot script is the only one there should be — if a second was added, this ' +
      'extraction is now picking the wrong one and the theme tests are testing nothing.',
  )
}

export const themeBootScript = matches[0][1]

// Runs it the way the browser does: as a classic script against the current document.
export function runThemeBootScript(): void {
  new Function(themeBootScript)()
}
