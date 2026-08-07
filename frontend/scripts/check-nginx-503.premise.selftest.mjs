// The premise BEYOND the confs (Scenario H9.4), split from check-nginx-503.selftest.mjs to keep both
// files under the line limit — that file owns the directive rules, this one owns everything else the
// carve-out rests on: the prose pointers surviving, and the ORIGIN itself never answering 503.
//
// These are the halves with no nginx directive to scan. They fail the same build, through the same
// guard, and are exercised the same way: fixtures in a temp dir, exit code plus the quoted offender.
import { mkdirSync, mkdtempSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { tmpdir } from 'node:os'
import { CLEAN_CONF, expectVerdict } from './nginx503SelftestHarness.mjs'
import { reportAndExit } from './selftestRunner.mjs'

// A doc with the bullet tidied away — the failure mode being pinned is a doc edit, so the fixture is
// a doc. Serves both pointer files: neither says anything about 503.
const NOTES_WITHOUT_POINTER = join(
  mkdtempSync(join(tmpdir(), 'nginx-503-notes-')),
  'architecture.md',
)
writeFileSync(
  NOTES_WITHOUT_POINTER,
  '# Architecture\n\n## Deploy notes\n\n- nothing about 503 here\n',
)

// A backend tree holding one source file, for the origin-scan cases. `name` may carry directories
// — the probe exemption is keyed on a path SEGMENT, so a case that cannot nest cannot reach it.
function backendFixture(name, contents) {
  const dir = mkdtempSync(join(tmpdir(), 'nginx-503-backend-'))
  const path = join(dir, name)
  mkdirSync(dirname(path), { recursive: true })
  writeFileSync(path, contents)
  return dir
}

const PROBE_SOURCE = 'return JSONResponse(status_code=503, content={"status": "unavailable"})\n'

// The ungated hops' only carrier. It lives in a doc, docs get restructured, and losing the bullet
// is silent — so the scan reads it the same way it reads the confs' back-reference.
expectVerdict({
  what: 'a deploy-notes file that lost the pointer fails',
  confs: { 'frontend.conf': CLEAN_CONF },
  deployNotes: NOTES_WITHOUT_POINTER,
  code: 1,
  quotes: ['no longer says mayHaveLandedServerSide'],
})

// The owed-items file carries the half of the premise no scan can enforce — a DELIBERATE 503. It is
// prose in a doc whose neighbouring note is meant to be deleted one day, so it is pinned like the
// deploy notes rather than trusted to survive a tidy-up.
expectVerdict({
  what: 'an owed-items file that lost its checkbox fails',
  confs: { 'frontend.conf': CLEAN_CONF },
  owedItems: NOTES_WITHOUT_POINTER,
  code: 1,
  quotes: ['No handler may return 503'],
})

expectVerdict({
  what: 'a deploy-notes file that was moved or renamed fails',
  confs: { 'frontend.conf': CLEAN_CONF },
  deployNotes: join(tmpdir(), 'nginx-503-no-such-architecture.md'),
  code: 1,
  quotes: ['does not exist'],
})

// The origin is the one hop that can 503 with nothing in front of it misbehaving, and a
// provider-outage HTTPException(503) is a natural thing for the backend to add. Reading backend/ is
// not editing it, and the frontend is the layer that breaks when the claim lapses.
expectVerdict({
  what: 'a backend that raises 503 fails',
  confs: { 'frontend.conf': CLEAN_CONF },
  backend: backendFixture(
    'handlers.py',
    'def unavailable():\n    raise HTTPException(status_code=503)\n',
  ),
  code: 1,
  quotes: ['the ORIGIN now mentions 503', 'status_code=503'],
})

// The boundary, same reasoning as the conf near-misses: a port, a timeout constant or a COMMENT
// explaining why no handler returns 503 must not fire, or the scan gets deleted the first time it
// does. Both live in one fixture so a single case pins the whole shape.
expectVerdict({
  what: 'a port, a longer number and a comment mentioning 503 do not fire',
  confs: { 'frontend.conf': CLEAN_CONF },
  backend: backendFixture(
    'settings.py',
    'PORT = 5030\nTIMEOUT_MS = 1503\n# never return 503 — see mayHaveLandedServerSide\n',
  ),
  code: 0,
})

// The container probe is the one route whose 503 cannot be the answer to a write: unauthenticated,
// outside `/api/v1`, and answered to the orchestrator. Exempt — otherwise the guard fires on the
// one endpoint whose 503 IS its contract, and a guard that fires on correct code gets deleted.
expectVerdict({
  what: 'the container probe route may answer 503',
  confs: { 'frontend.conf': CLEAN_CONF },
  backend: backendFixture('router/health/health_router.py', PROBE_SOURCE),
  code: 0,
})

// The exemption's own boundary, and the reason it is keyed on a path SEGMENT. A module merely
// NAMED for health is application code on the versioned API — exactly where a provider-outage 503
// would be added — and a filename-substring rule would have waved it through.
expectVerdict({
  what: 'a module named for health but not under a health/ directory still fires',
  confs: { 'frontend.conf': CLEAN_CONF },
  backend: backendFixture('router/health_metrics_api.py', PROBE_SOURCE),
  code: 1,
  quotes: ['the ORIGIN now mentions 503', 'status_code=503'],
})

reportAndExit({
  subject: 'nginx 503 premise',
  subjectIs: 'the premise beyond the confs',
  script: 'check-nginx-503.mjs',
  tail: 'the deploy-notes pointer, the owed-items pointer, and the origin scan with its boundary.',
})
