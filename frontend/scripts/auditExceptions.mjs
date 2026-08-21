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
  // Empty, and that is the wanted state. It last held two rows for GHSA-qwww-vcr4-c8h2 against
  // `react-router` and `react-router-dom` — React Router's RSC mode running an action request
  // before the 400 that should have rejected it, which this Vite SPA was never exposed to. They
  // were removed on 2026-08-21 because `npm audit --omit=dev` stopped reporting the advisory at
  // all, and the gate fails on a listed advisory npm no longer reports: a ledger that keeps stale
  // rows is one nobody trusts to be read.
]
