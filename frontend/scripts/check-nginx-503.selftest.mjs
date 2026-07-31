// The guard's guard (Scenario H9.4).
//
// check-nginx-503.mjs is a CI gate whose PASS output and whose broken-no-op output are the same
// line in the log. Narrow its directive list, break the path resolution, or invert the offender
// push, and a step named `nginx 503 guard` prints OK forever — the same "config that looks like a
// gate and gates nothing" failure frontend-ci.yml's own header calls out one layer down.
//
// So the gate is driven against fixture confs here: each case asserts an exit code, and the failing
// ones assert the offending line is actually quoted (an exit 1 with an empty message would still
// pass a bare code check while telling the reader nothing). The mutation checks behind the original
// commits were one-time manual runs; this is what preserves them.
//
// This file is the CASES. How a fixture is built, how the guard is invoked and how a verdict is
// recorded live in nginx503SelftestHarness.mjs.
import { existsSync } from 'node:fs'
import { join } from 'node:path'
import { tmpdir } from 'node:os'
import { DIRECTIVES, DIRECTIVES_THAT_CAN_EMIT_503 } from './nginx503Directives.mjs'
import { mkdtempSync, writeFileSync } from 'node:fs'
import {
  BACK_REFERENCE,
  CLEAN_CONF,
  REAL_MONOREPO_MARKER,
  confDeclaring,
  expectVerdict,
  runGuard,
} from './nginx503SelftestHarness.mjs'
import { check, countCase, reportAndExit } from './selftestRunner.mjs'

// A deploy-notes file with the bullet tidied away — the failure mode being pinned is a doc edit, so
// the fixture is a doc.
const NOTES_WITHOUT_POINTER = join(mkdtempSync(join(tmpdir(), 'nginx-503-notes-')), 'architecture.md')
writeFileSync(NOTES_WITHOUT_POINTER, '# Architecture\n\n## Deploy notes\n\n- nothing about 503 here\n')

// A conf that proxies to the origin and can answer nothing itself: the only shape that may pass.
expectVerdict({ what: 'a clean conf passes', confs: { 'frontend.conf': CLEAN_CONF }, code: 0 })

// Generating the cases from the shared list closes one hole and opens another: an entry can no
// longer exist without a case, but DELETING an entry deletes its case too and everything stays
// green. So the list itself is pinned by name — dropping `max_fails` now fails here, and the reader
// who wants it gone has to say so in this file, where the reason it was scanned is written down.
check(
  'the scanned list still covers every 503 route',
  DIRECTIVES.join() ===
    '503,limit_req,limit_conn,error_page,proxy_intercept_errors,max_fails,proxy_next_upstream,upstream',
  `the list changed to: ${DIRECTIVES.join()}`,
)

// One case per entry in the scanned list, generated FROM that list: a directive silently dropped
// from the scan cannot leave the self-test still reporting the same number of green cases, because
// there is no way to express an entry without a case. `return 503` leads — it is the case the guard
// shipped unable to catch, printing OK over a conf that 503'd every request.
for (const { directive, samples, nearMisses = [] } of DIRECTIVES_THAT_CAN_EMIT_503) {
  for (const sample of samples) {
    // The attribution is asserted, not just the exit code: `firstFiring` returns the FIRST matching
    // entry, so a sample whose line also trips an earlier entry proves nothing about this one. The
    // `upstream` sample did exactly that — it carried `max_fails` on the same line, was reported as
    // `max_fails`, and the entry could be blinded outright with all cases green.
    expectVerdict({
      what: `\`${directive}\` fails on \`${sample}\``,
      confs: { 'frontend.conf': confDeclaring(sample) },
      code: 1,
      quotes: [sample, `(\`${directive}\`)`],
    })

    // A trailing comment must not talk the guard out of firing. Every negating predicate reads a
    // substring of the line — `off`, `max_fails=0`, a non-5xx code — so before comments were cut,
    // `proxy_intercept_errors on;  # never off` scanned clean while answering 503.
    if (nearMisses.length === 0) continue
    expectVerdict({
      what: `\`${directive}\` still fires with a trailing comment`,
      confs: { 'frontend.conf': confDeclaring(`${sample}  # ${nearMisses[0]}`) },
      code: 1,
      quotes: [`(\`${directive}\`)`],
    })
  }

  // The other half of the boundary. An entry with a benign neighbouring form pins that form as
  // PASSING: firing on `error_page 404 /index.html;` or a bare `upstream` block is not a harmless
  // false positive, it is how the guard gets deleted — the author sees a commit that plainly cannot
  // endanger an autosave failing a check that says it does, and concludes the check is wrong.
  for (const nearMiss of nearMisses) {
    expectVerdict({
      what: `\`${directive}\` does not fire on \`${nearMiss}\``,
      confs: { 'frontend.conf': confDeclaring(nearMiss) },
      code: 0,
    })
  }
}

// The companion condition is about the whole conf, not one line — every generated case above keeps
// its directive on a single line, so the cross-line path it exists for would otherwise be unrun.
expectVerdict({
  what: '`upstream` fires when the companion sits on ANOTHER line',
  confs: {
    'frontend.conf': `${BACK_REFERENCE}upstream backend { server backend:8000; }
server {
    proxy_next_upstream error timeout;
}
`,
  },
  code: 1,
  quotes: ['(`upstream`)'],
})

// The comment-stripping is load-bearing in the other direction too: the real conf's back-reference
// NAMES every scanned directive, so a scan of raw text would fire on the guard's own explanation.
expectVerdict({
  what: 'a comment naming the directives does not fire',
  confs: {
    'frontend.conf': `${BACK_REFERENCE}# do not add limit_req, error_page, return 503 or proxy_next_upstream here\n${CLEAN_CONF}`,
  },
  code: 0,
})

// The pointer is what the hops OUTSIDE this repo have instead of a gate. Deleting it is silent.
expectVerdict({
  what: 'losing the back-reference fails',
  confs: { 'frontend.conf': 'server {\n    listen 80;\n}\n' },
  code: 1,
  quotes: ['mayHaveLandedServerSide'],
})

// Demanded of the DIRECTORY, not each file: a second conf for static caching or a healthcheck
// listener proxies nothing to the origin and has no reason to carry the warning.
expectVerdict({
  what: 'a second conf without the back-reference passes while one conf has it',
  confs: { 'frontend.conf': CLEAN_CONF, 'health.conf': 'server {\n    listen 8081;\n}\n' },
  code: 0,
})

// Both ways of ending up with nothing to scan. The second is the one that used to exit 0 with a
// reassuring line, because a missing directory is ambiguous between "split repo" and "moved".
expectVerdict({ what: 'an empty conf directory fails', confs: {}, code: 1 })
expectVerdict({ what: 'a missing conf directory fails in the monorepo shape', confs: null, code: 1 })

// The shape the guard exists to stay safe in: `frontend/` as the repository ROOT, where infra/ does
// not exist and never did. Without this case the missing-directory case above silently demanded
// exit 1 everywhere, and `check:ingress` — which runs this self-test FIRST — turned the split
// repo's clean skip into a hard failure, breaking the very both-shapes property being guarded.
expectVerdict({
  what: 'a missing conf directory is a SKIP in the split-repo shape',
  confs: null,
  // A marker path that does not exist IS the split shape — in that repo `frontend/` is the root, so
  // the monorepo workflow two levels up is simply not there.
  marker: join(tmpdir(), 'nginx-503-no-such-frontend-ci.yml'),
  code: 0,
})

// The default path, with no flags at all — the one CI actually takes. Every other case overrides
// the directory, so without this the resolution that matters is never executed: repoint it at any
// directory holding one benign conf and all the other cases stay green over an unscanned ingress.
//
// The expected verdict is whatever THIS checkout's shape implies, read the same way the guard reads
// it. In the monorepo that is a scan naming frontend.conf; in the split repo, where frontend/ is the
// root and infra/ never existed, it is the documented skip — and asserting the monorepo answer there
// is what turned that repo's clean skip into a hard failure once check:ingress ran this first.
countCase()
const monorepoHere = existsSync(REAL_MONOREPO_MARKER)
const real = runGuard({ marker: null })
const expected = monorepoHere ? 'frontend.conf' : 'skipped'
check(
  `with no flags the guard ${monorepoHere ? 'scans the real ingress' : 'skips (split-repo shape)'}`,
  real.code === 0 && real.output.includes(expected),
  `expected exit 0 mentioning ${JSON.stringify(expected)}, got ${real.code}:
${real.output}`,
)

reportAndExit({
  subject: 'nginx 503 guard',
  subjectIs: 'the guard',
  script: 'check-nginx-503.mjs',
  tail:
    'one per scanned directive plus each benign near-miss, the clean conf, comments, the\n' +
    'back-reference in the confs AND in the deploy notes, a second conf, an empty directory,\n' +
    'a moved directory, the split-repo skip,\n' +
    'and the real ingress with no flags.',
})
