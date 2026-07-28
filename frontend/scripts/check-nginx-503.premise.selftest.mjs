// The premise BEYOND the confs (Scenario H9.4), split from check-nginx-503.selftest.mjs to keep both
// files under the line limit — that file owns the directive rules, this one owns everything else the
// carve-out rests on: the prose pointers surviving, and the ORIGIN itself never answering 503.
//
// These are the halves with no nginx directive to scan. They fail the same build, through the same
// guard, and are exercised the same way: fixtures in a temp dir, exit code plus the quoted offender.
import { mkdtempSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { tmpdir } from 'node:os'
import { CLEAN_CONF, expectVerdict } from './nginx503SelftestHarness.mjs'
import { reportAndExit } from './selftestRunner.mjs'

// A doc with the bullet tidied away — the failure mode being pinned is a doc edit, so the fixture is
// a doc. Serves both pointer files: neither says anything about 503.
const NOTES_WITHOUT_POINTER = join(mkdtempSync(join(tmpdir(), 'nginx-503-notes-')), 'architecture.md')
writeFileSync(NOTES_WITHOUT_POINTER, '# Architecture\n\n## Deploy notes\n\n- nothing about 503 here\n')

// A backend tree holding one source file, for the origin-scan cases.
function backendFixture(name, contents) {
  const dir = mkdtempSync(join(tmpdir(), 'nginx-503-backend-'))
  writeFileSync(join(dir, name), contents)
  return dir
}

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
  backend: backendFixture('handlers.py', 'def unavailable():\n    raise HTTPException(status_code=503)\n'),
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

reportAndExit({
  subject: 'nginx 503 premise',
  subjectIs: 'the premise beyond the confs',
  script: 'check-nginx-503.mjs',
  tail: 'the deploy-notes pointer, the owed-items pointer, and the origin scan with its boundary.',
})
