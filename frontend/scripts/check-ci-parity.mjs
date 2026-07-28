// Two CI files gate this code, because `frontend/` is published both as a directory of the
// monorepo and as the ROOT of a separate repo (gitverse slide_frontend). Their headers say they
// are "kept in step by hand", and hand-kept parity is the kind that holds until the day it
// matters: the split repo would keep passing an older gate, silently, with nothing red anywhere.
//
// This checks the ONE thing that must match — the set of quality commands each pipeline runs.
// Everything else about the two files is legitimately different (triggers, working-directory,
// cache paths, the docker job that only the monorepo has), so nothing else is compared.
import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { bodyProblems, scanPipeline } from './ciPipelineScan.mjs'

const here = dirname(fileURLToPath(import.meta.url))
const STANDALONE = {
  label: 'frontend/.github/workflows/ci.yml',
  path: resolve(here, '../.github/workflows/ci.yml'),
}
const MONOREPO = {
  label: '.github/workflows/frontend-ci.yml',
  path: resolve(here, '../../.github/workflows/frontend-ci.yml'),
}

const PACKAGE_JSON = resolve(here, '../package.json')

// Sameness is not presence: two identical pipelines that run NOTHING satisfy the comparison below,
// and so does deleting one step from both files in the same commit. That is the shape of the
// failure this file exists to prevent, one level up — every gate here is a step someone under
// release pressure can remove, and the only thing that noticed would be this comparison, which
// removal keeps green.
//
// So the gates are named. Each entry says what is lost when it goes, because a bare list gets
// pruned as clutter and a reason does not. `mustContain` pins the part of a composite body the
// reason depends on — a name in a workflow says nothing about what the script still does.
const REQUIRED = [
  { script: 'typecheck', why: 'tsc -b; without it a broken build reaches main invisibly (vitest strips types)' },
  {
    script: 'test:coverage',
    why: 'the suite AND the per-file coverage floors, which only fire under --coverage',
    mustContain: ['--coverage', 'check-per-file-coverage.mjs'],
  },
  { script: 'build', why: 'the one step that proves the app still compiles and bundles' },
  { script: 'lint', why: 'oxlint at --max-warnings=0', mustContain: ['--max-warnings=0'] },
  { script: 'format:check', why: 'a .prettierrc nobody runs is a preference, not a convention' },
  { script: 'audit', why: 'production dependency advisories at high and above' },
  { script: 'ci:parity', why: 'this check; a pipeline that drops it can then drift freely' },
  {
    script: 'check:ingress',
    why: 'the nginx 503 guard behind mayHaveLandedServerSide — see that predicate',
    mustContain: ['check-nginx-503.selftest.mjs', 'check-nginx-503.mjs'],
  },
]

function isBelowFloor({ label, path }, { active, neutralized }) {
  const missing = REQUIRED.filter(({ script }) => !active.includes(script))
  if (missing.length === 0) return false

  console.error(`CI gate missing from ${label}:`)
  for (const { script, why } of missing) {
    // A neutralized step is the more likely of the two and reads as present to anyone skimming the
    // file, so it is named as such rather than reported as absent.
    const dead = neutralized.includes(script)
    console.error(`  npm run ${script} — ${dead ? 'present but behind `if:`/`continue-on-error`' : 'absent'}: ${why}`)
  }
  console.error(`  (${path})`)
  return true
}

// Every pipeline is checked before exiting, so one run reports every missing gate rather than only
// the first file's.
function exitIfBelowFloor(...checked) {
  const problems = bodyProblems(PACKAGE_JSON, REQUIRED)
  if (problems.length > 0) {
    console.error('CI gate hollowed out in package.json — the workflows still name it:')
    for (const problem of problems) console.error(problem)
  }
  if (!checked.map((args) => isBelowFloor(...args)).some(Boolean) && problems.length === 0) return
  console.error('Restore the step; do not remove or neutralize a gate to make a pipeline pass.')
  process.exit(1)
}

// Neither workflow present is the shape of an export of `frontend/` with no CI at all. Reading
// STANDALONE unconditionally would crash there with a raw ENOENT — a stack trace where the intended
// answer is a clean skip, and one indistinguishable from a real gate failure in a CI log.
if (!existsSync(STANDALONE.path)) {
  if (existsSync(MONOREPO.path)) {
    console.error(`CI parity: ${MONOREPO.label} is here but ${STANDALONE.label} is not.`)
    console.error('The standalone copy is what gates the split repo — restore it or move it back.')
    process.exit(1)
  }
  console.log('CI parity skipped — no frontend workflow here at all (no CI to compare or floor).')
  process.exit(0)
}

const standalone = scanPipeline(STANDALONE.path)

// In the split repo there IS no monorepo workflow — `frontend/` is the root there, and the
// counterpart file simply does not exist. Nothing to COMPARE is not a failure; the same command
// has to be safe to run in both repository shapes or it cannot live in package.json. The floor
// still applies to the pipeline that is here, since that is the one gating that repo.
if (!existsSync(MONOREPO.path)) {
  exitIfBelowFloor([STANDALONE, standalone])
  console.log('CI parity skipped — no monorepo workflow here (standalone repository shape).')
  console.log(`Required gates present: ${REQUIRED.map(({ script }) => script).join(', ')}`)
  process.exit(0)
}

const monorepo = scanPipeline(MONOREPO.path)

exitIfBelowFloor([STANDALONE, standalone], [MONOREPO, monorepo])

if (standalone.active.join() !== monorepo.active.join()) {
  const onlyStandalone = standalone.active.filter((s) => !monorepo.active.includes(s))
  const onlyMonorepo = monorepo.active.filter((s) => !standalone.active.includes(s))
  console.error('CI drift: the two frontend pipelines no longer run the same npm scripts.')
  console.error(`  ${STANDALONE.label} : ${standalone.active.join(', ') || '(none)'}`)
  console.error(`  ${MONOREPO.label}: ${monorepo.active.join(', ') || '(none)'}`)
  if (onlyStandalone.length) console.error(`  only in the standalone copy: ${onlyStandalone}`)
  if (onlyMonorepo.length) console.error(`  only in the monorepo copy:   ${onlyMonorepo}`)
  console.error('Add the missing step to the other file; do not delete one to make this pass.')
  process.exit(1)
}

console.log(`CI parity OK — both pipelines run: ${monorepo.active.join(', ')}`)
