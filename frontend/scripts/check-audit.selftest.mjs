// The advisory gate's guard.
//
// check-audit.mjs is the only thing standing between a fresh production advisory and a green
// pipeline, and every way it can fail silently ends the same way: an OK line over a report nobody
// read. Invert the unlisted filter, compare expiry dates the wrong way round, or mis-walk npm's
// `via` chains and the gate keeps printing OK. So each of those is a case here, driven against
// FIXTURE reports — the real registry cannot be asked for an expired exemption on demand.
import { fileURLToPath } from 'node:url'
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { tmpdir } from 'node:os'
import { checkVerdict, reportAndExit, runNodeScript } from './selftestRunner.mjs'

const here = dirname(fileURLToPath(import.meta.url))
const CHECK = resolve(here, 'check-audit.mjs')

// Dates are pinned rather than derived from the clock: a case that reads `new Date()` passes today
// and starts failing on a date nobody chose, which is the failure mode that gets self-tests deleted.
const BEFORE = '2020-01-01'
const AFTER = '2099-01-01'

// A ledger of the self-test's OWN, not the project's. Deriving the fixtures from
// `auditExceptions.mjs` read well while that file had rows in it, and stopped testing anything the
// day it was emptied: with no accepted entry there is no accepted verdict and no expiry to pass,
// so two of the six cases quietly became assertions about an empty list. These two rows exist to
// be accepted and to expire, and nothing about the real ledger can take that away.
const FIXTURE_LEDGER = [
  {
    ghsa: 'GHSA-2222-2222-2222',
    package: 'accepted-lib',
    severity: 'high',
    why: 'fixture: the code path this advisory needs is not reachable here',
    expires: '2030-01-01',
    revisit: 'fixture: upgrade accepted-lib',
  },
  {
    ghsa: 'GHSA-3333-3333-3333',
    package: 'other-accepted-lib',
    severity: 'moderate',
    why: 'fixture: a second row, so the gate is exercised on more than one entry',
    expires: '2030-01-01',
    revisit: 'fixture: upgrade other-accepted-lib',
  },
]

// One advisory object per accepted entry, so the fixture that stands for "nothing unexpected" is
// generated from that ledger and cannot drift out of step with it.
const advisory = ({ ghsa, severity }, title) => ({
  source: 1,
  name: 'x',
  url: `https://github.com/advisories/${ghsa}`,
  severity,
  title,
})

const reportOf = (vulnerabilities) => JSON.stringify({ auditReportVersion: 2, vulnerabilities })

const LEDGER_ONLY = reportOf(
  Object.fromEntries(
    FIXTURE_LEDGER.map((entry) => [
      entry.package,
      {
        name: entry.package,
        severity: entry.severity,
        via: [advisory(entry, 'the accepted advisory')],
      },
    ]),
  ),
)

// The fixture ledger is written to disk per case and handed over with `--ledger`, the same way the
// report is: the gate loads it as a module, so it has to be a file, and a temporary one keeps the
// cases from depending on each other.
function expect({ what, report, today = BEFORE, code, quotes = [], ledger = FIXTURE_LEDGER }) {
  const dir = mkdtempSync(join(tmpdir(), 'check-audit-'))
  const path = join(dir, 'report.json')
  const ledgerPath = join(dir, 'ledger.mjs')
  writeFileSync(path, report)
  writeFileSync(
    ledgerPath,
    `export const ACCEPTED = ${JSON.stringify(ledger, null, 2)}
`,
  )
  checkVerdict({
    what,
    result: runNodeScript(CHECK, [
      `--report=${path}`,
      `--today=${today}`,
      `--ledger=${ledgerPath}`,
    ]),
    code,
    quotes,
  })
  rmSync(dir, { recursive: true, force: true })
}

expect({
  what: 'a report with no vulnerabilities and an empty ledger passes',
  report: reportOf({}),
  ledger: [],
  code: 0,
  quotes: ['no production advisories'],
})

// The STALE case, and the reason the ledger is a parameter: every accepted row here describes
// something the report does not contain. An entry earns its keep only while npm still reports the
// finding it explains, and this is the half of the contract that the real ledger — now empty —
// cannot exercise on its own.
expect({
  what: 'a ledger row npm no longer reports is a failure, not a pass',
  report: reportOf({}),
  code: 1,
  quotes: ['no longer reports it'],
})

expect({
  what: 'exactly the accepted advisories, before their expiry, passes',
  report: LEDGER_ONLY,
  code: 0,
  quotes: ['accepted, unexpired exception'],
})

expect({
  what: 'the same advisories after their expiry date fail',
  report: LEDGER_ONLY,
  today: AFTER,
  code: 1,
  quotes: ['the exception expired on', 'Recheck it'],
})

// The case the threshold used to swallow. A low severity is deliberate: `--audit-level=high` was
// green about exactly this, and the point of the ledger is that severity no longer decides.
expect({
  what: 'an unlisted low-severity advisory fails',
  ledger: [],
  report: reportOf({
    'some-lib': {
      name: 'some-lib',
      severity: 'low',
      via: [
        {
          source: 2,
          name: 'some-lib',
          url: 'https://github.com/advisories/GHSA-0000-0000-0000',
          severity: 'low',
          title: 'Prototype pollution',
        },
      ],
    },
  }),
  code: 1,
  quotes: ['GHSA-0000-0000-0000', 'Prototype pollution', 'auditExceptions.mjs'],
})

// npm reports a direct dependency's exposure as a bare package NAME in `via`, with the advisory
// text living on the package it points at. Dropping those leaves a real finding invisible.
expect({
  what: 'an advisory reached only through a `via` package name is still reported',
  ledger: [],
  report: reportOf({
    inner: {
      name: 'inner',
      severity: 'critical',
      via: [
        {
          source: 3,
          name: 'inner',
          url: 'https://github.com/advisories/GHSA-1111-1111-1111',
          severity: 'critical',
          title: 'Remote code execution',
        },
      ],
    },
    outer: { name: 'outer', severity: 'critical', via: ['inner'] },
  }),
  code: 1,
  quotes: ['outer — GHSA-1111-1111-1111', 'inner — GHSA-1111-1111-1111'],
})

expect({
  what: 'a report that is not JSON is a failure, not an empty pass',
  ledger: [],
  report: 'npm ERR! network request failed',
  code: 1,
  quotes: ['no parseable report'],
})

reportAndExit({
  subject: 'Dependency audit',
  subjectIs: 'check-audit.mjs',
  script: 'scripts/check-audit.mjs',
  tail: 'clean report, stale row, ledger match, expiry, unlisted low, transitive via, unparseable report',
})
