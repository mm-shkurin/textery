// The parity check's guard.
//
// check-ci-parity.mjs decides whether eight CI gates exist at all, and until now nothing tested it:
// narrow REQUIRED, invert isBelowFloor's return, or break the path resolution, and `ci:parity`
// prints OK forever while the pipelines it vouches for run nothing. That is the same disease the
// sibling nginx guard was given a self-test for — this file is the same remedy, one script over.
//
// Cases are driven against FIXTURE workflows written to a temp dir, so the real ones are never
// touched, and generated from REQUIRED itself so a gate cannot be added without a case. What those
// fixtures look like lives in ciParitySelftestHarness.mjs; this file is the cases.
import { fileURLToPath } from 'node:url'
import { existsSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { REQUIRED } from './ciRequiredGates.mjs'
import { check, countCase, reportAndExit, runNodeScript } from './selftestRunner.mjs'
import { ALL, CHECK, expect, packageJson, step } from './ciParitySelftestHarness.mjs'

const here = dirname(fileURLToPath(import.meta.url))

expect({
  what: 'two complete, identical pipelines pass',
  code: 0,
  // Pinned to the comparison branch's own line: exit 0 alone cannot tell a real pass from the
  // no-workflows-here SKIP, which also exits 0 and also reads as success in a log.
  quotes: ['CI parity OK — both pipelines run'],
})

// The floor's whole reason for existing: removing a gate from BOTH files keeps the sameness
// comparison green, so only a named list can notice. One case per gate, generated from the list.
for (const { script } of REQUIRED) {
  const without = ALL.filter((name) => name !== script)
  expect({
    what: `dropping \`${script}\` from both pipelines fails`,
    standalone: without,
    monorepo: without,
    code: 1,
    quotes: [`npm run ${script}`],
  })
}

// Neutering is cheaper than deleting and looks temporary, which is why it is what gets reached for.
expect({
  what: 'a gate behind `if:` counts as missing',
  raw: {
    monorepo: `jobs:\n  gate:\n    steps:\n${ALL.map((s) => `      - name: ${s}\n        if: false\n        run: npm run ${s}\n`).join('')}`,
  },
  code: 1,
  quotes: ['present but behind'],
})

expect({
  what: 'a gate marked continue-on-error counts as missing',
  raw: {
    monorepo: `jobs:\n  gate:\n    steps:\n      - name: typecheck\n        continue-on-error: true\n        run: npm run typecheck\n${ALL.filter(
      (s) => s !== 'typecheck',
    )
      .map(step)
      .join('')}`,
  },
  code: 1,
  quotes: ['present but behind'],
})

// The workflows name gates; package.json holds their bodies, and hollowing one there leaves both
// pipelines and the floor untouched.
expect({
  what: 'a required script missing from package.json fails',
  pkg: JSON.stringify({
    scripts: Object.fromEntries(ALL.filter((s) => s !== 'build').map((s) => [s, `node ${s}`])),
  }),
  code: 1,
  quotes: ['no such script in package.json'],
})

expect({
  what: 'a composite script that lost its pinned half fails',
  pkg: packageJson({ 'check:ingress': 'node scripts/check-nginx-503.mjs' }),
  code: 1,
  quotes: ['no longer runs check-nginx-503.selftest.mjs'],
})

// The original job: the two pipelines drifting apart.
expect({
  what: 'a gate present in only one pipeline fails as drift',
  monorepo: [...ALL, 'extra:gate'],
  pkg: packageJson({ 'extra:gate': 'node extra' }),
  code: 1,
  quotes: ['CI drift'],
})

// Both repository shapes that legitimately have one file, plus the one that has neither.
expect({
  what: 'the split-repo shape skips the comparison but keeps the floor',
  monorepo: null,
  code: 0,
  quotes: ['Required gates present'],
})
expect({
  what: 'the split-repo shape still fails below the floor',
  monorepo: null,
  standalone: ALL.filter((s) => s !== 'lint'),
  code: 1,
  quotes: ['npm run lint'],
})
expect({
  what: 'a monorepo workflow with no standalone copy fails',
  standalone: null,
  code: 1,
  quotes: ['The standalone copy is what gates the split repo'],
})
expect({
  what: 'neither workflow present is a clean skip',
  standalone: null,
  monorepo: null,
  code: 0,
  quotes: ['no frontend workflow here at all'],
})

// Conditioning the whole JOB is cheaper than conditioning eight steps and reads as ordinary
// workflow hygiene. It also lives above the first `- `, where step chunking cannot see it.
expect({
  what: 'a job-level `if:` counts every gate under it as missing',
  raw: {
    monorepo: `jobs:
  gate:
    if: false
    steps:
${ALL.map(step).join('')}`,
  },
  code: 1,
  quotes: ['present but behind'],
})

// The mirror image, and the more likely one: the real monorepo file is TWO jobs, and the second is
// exactly where `if: github.event_name == 'push'` gets written. Chunking that swallowed the next
// job's keys into the previous job's last step made a gate nobody touched read as neutralized, and
// CI hard-failed pointing at it — a false positive is how a gate gets deleted.
expect({
  what: "a SECOND job's `if:` leaves the first job's gates active",
  raw: {
    monorepo: `jobs:
  gate:
    steps:
${ALL.map(step).join('')}  docker:
    if: github.event_name == 'push'
    needs: gate
    steps:
      - run: docker build .
`,
  },
  code: 0,
})

// Generating from REQUIRED means an entry cannot exist without a case — and deleting an entry
// deletes its case too, so the list is pinned by name as well.
check(
  'the required-gate list still names every gate',
  ALL.join() === 'typecheck,test:coverage,build,lint,format:check,audit,ci:parity,check:ingress',
  `the list changed to: ${ALL.join()}`,
)

// The default path resolution, with no flags at all — the one CI actually takes. Every case above
// overrides all three paths, so the `resolve(here, '../..')` the real run depends on is otherwise
// never executed. It is the worst of the three motivating mutations to leave unpinned: a typo'd
// default lands in the «no frontend workflow here at all» branch, which prints a plausible success
// line and exits 0 forever, in exactly the repository shape this check is supposed to gate.
countCase()
const bare = runNodeScript(CHECK, [])
const monorepoHere = existsSync(resolve(here, '../../.github/workflows/frontend-ci.yml'))
const expected = monorepoHere ? 'CI parity OK — both pipelines run' : 'Required gates present'
check(
  'with no flags the check reads the real pipelines rather than skipping',
  bare.code === 0 && bare.output.includes(expected),
  `expected exit 0 mentioning ${JSON.stringify(expected)}, got ${bare.code}:
${bare.output}`,
)

reportAndExit({
  subject: 'CI parity',
  subjectIs: 'the parity check',
  script: 'check-ci-parity.mjs',
  tail:
    'one per required gate, plus step- and job-level neutering, package.json hollowing,\n' +
    'drift, all three repository shapes, and the real pipelines with no flags.',
})
