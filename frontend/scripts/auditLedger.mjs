// Judging an `npm audit --json` report against the written exception ledger.
//
// Split from check-audit.mjs so the verdict can be exercised on fixture reports without spawning
// npm — the self-test needs an expired exception and an unlisted critical, and neither is something
// a registry can be asked for on demand.
import { ACCEPTED } from './auditExceptions.mjs'

const key = ({ ghsa, package: pkg }) => `${pkg}|${ghsa}`

// `via` mixes two kinds of entry: an advisory object for a package vulnerable in its own right, and
// a bare package NAME for one that is only vulnerable through a dependency. Both are reported —
// the second is how a direct dependency shows up — so the name form is resolved back to the
// advisories of the package it points at rather than dropped for having no url of its own.
function findingsFor(name, entry, vulnerabilities) {
  return entry.via.flatMap((via) => {
    if (typeof via !== 'string') {
      return [{ package: name, ghsa: ghsaOf(via.url), severity: via.severity, title: via.title }]
    }
    const target = vulnerabilities[via]
    if (!target || target === entry) return []
    return findingsFor(name, target, vulnerabilities).map((found) => ({ ...found, package: name }))
  })
}

// The advisory id is the stable identity — the title gets reworded and the numeric `source` is a
// registry-internal id. A url that is not a GitHub advisory link leaves the id null, which no
// ledger entry can match, so the finding reports as unlisted rather than matching by accident.
function ghsaOf(url) {
  const match = /GHSA-[\w-]+/.exec(url ?? '')
  return match ? match[0] : null
}

export function findings(report) {
  const vulnerabilities = report.vulnerabilities ?? {}
  const seen = new Map()

  for (const [name, entry] of Object.entries(vulnerabilities)) {
    for (const found of findingsFor(name, entry, vulnerabilities)) seen.set(key(found), found)
  }

  return [...seen.values()]
}

// Three ways this can be wrong, and all three are reported in one run: an advisory nobody wrote
// down, an exemption whose date has passed, and a row describing something npm no longer reports.
// The last one is not cosmetic — a ledger carrying rows that no longer mean anything is one a
// reader starts skimming, and skimming is how the first kind gets waved through.
export function problems(report, today) {
  const found = findings(report)
  const accepted = new Map(ACCEPTED.map((entry) => [key(entry), entry]))
  const listed = []

  const unlisted = found.filter((finding) => {
    const entry = accepted.get(key(finding))
    if (entry) listed.push({ finding, entry })
    return !entry
  })

  return [
    ...unlisted.map(
      (finding) =>
        `  ${finding.package} — ${finding.ghsa ?? '(no advisory id)'} (${finding.severity}): ${finding.title}\n` +
        '    Not in scripts/auditExceptions.mjs. Upgrade the dependency, or add an entry saying why this application is not exposed and when that stops being accepted.',
    ),
    ...listed
      .filter(({ entry }) => entry.expires <= today)
      .map(
        ({ finding, entry }) =>
          `  ${finding.package} — ${finding.ghsa}: the exception expired on ${entry.expires} (today is ${today}).\n` +
          `    Recheck it. Fix: ${entry.revisit}. Extending the date is a decision to be made again, not a formality.`,
      ),
    ...ACCEPTED.filter((entry) => !found.some((finding) => key(finding) === key(entry))).map(
      (entry) =>
        `  ${entry.package} — ${entry.ghsa}: listed as accepted, but npm audit no longer reports it.\n` +
        '    Delete the entry; a stale ledger is one nobody reads.',
    ),
  ]
}
