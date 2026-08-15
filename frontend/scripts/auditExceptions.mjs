// The advisories this project knowingly ships with, and for how long.
//
// The previous gate was `npm audit --omit=dev --audit-level=high`. A threshold is a silent
// allowlist: it exempts every present and FUTURE advisory below the line without naming one, so
// nobody can tell an accepted risk from an unread one, and the day a moderate turns out to matter
// the gate is already green about it. Raising the threshold is also the obvious way to make this
// gate stop complaining, which is exactly the move it should make expensive.
//
// So the threshold is gone and the exemptions are written down instead. Each entry names the
// advisory, why this application is not exposed, and the date the exemption stops being accepted —
// after which the gate goes red whether or not anything about the advisory changed. An exception
// without an expiry is a permanent decision made by whoever was in a hurry.
//
// An entry is also wrong when it stops matching: check-audit.mjs fails on a listed advisory that
// npm no longer reports, because a ledger that keeps stale rows is one nobody trusts to be read.
export const ACCEPTED = [
  {
    ghsa: 'GHSA-qwww-vcr4-c8h2',
    package: 'react-router',
    severity: 'high',
    // The advisory is scoped to React Router's RSC mode: a server receives an action request and
    // runs it before the 400 that should have rejected it. This app has no server side of React
    // Router at all — it is a Vite SPA, `BrowserRouter` in src/main.tsx, no loaders, no actions, no
    // `@vitejs/plugin-rsc`, and the API it talks to is the separate backend behind its own CSRF
    // story. There is no upgrade that clears it: every version <=7.17.0 carries fourteen advisories
    // of its own (open redirect, SSR XSS, deserialization RCE), so 7.18.2 is the least-exposed
    // release that exists, not a deferral of a fix that was available.
    why: 'RSC-mode only; this is a client-rendered SPA with no React Router server, no loaders and no actions',
    expires: '2026-11-01',
    revisit: 'react-router >=8.3.0, or the first 7.x release the advisory range excludes',
  },
  {
    ghsa: 'GHSA-qwww-vcr4-c8h2',
    package: 'react-router-dom',
    // npm reports the same advisory a second time against the direct dependency that pulls the
    // vulnerable one in. Listed separately because the gate matches on the pair, and a single row
    // would leave the second finding unexplained.
    severity: 'high',
    why: 'the same advisory, reported again through the direct dependency on react-router',
    expires: '2026-11-01',
    revisit: 'react-router >=8.3.0, or the first 7.x release the advisory range excludes',
  },
]
