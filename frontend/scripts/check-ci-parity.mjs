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
import { bodyProblems, runtimeProblems, scanPipeline } from './ciPipelineScan.mjs'
import { pinProblems } from './ciActionPins.mjs'
import { orderProblems, pathsProblems } from './ciTriggers.mjs'
import { REQUIRED } from './ciRequiredGates.mjs'

const here = dirname(fileURLToPath(import.meta.url))

// Overridable only through explicit CLI flags, and only so the self-test can point this check at
// fixture workflows. Not environment variables: an ambient value exported by a runner would
// redirect the real check while printing the same OK line, where a flag has to be typed into the
// step a reader can see. CI passes none, so the defaults are the real pipelines.
function flag(name, fallback) {
  const match = process.argv.slice(2).find((arg) => arg.startsWith(`--${name}=`))
  return match ? resolve(match.slice(name.length + 3)) : fallback
}

const STANDALONE = {
  label: 'frontend/.github/workflows/ci.yml',
  path: flag('standalone', resolve(here, '../.github/workflows/ci.yml')),
}
const MONOREPO = {
  label: '.github/workflows/frontend-ci.yml',
  path: flag('monorepo', resolve(here, '../../.github/workflows/frontend-ci.yml')),
}

const PACKAGE_JSON = flag('package', resolve(here, '../package.json'))

function isBelowFloor({ label, path }, { active, neutralized }) {
  const missing = REQUIRED.filter(({ script }) => !active.includes(script))
  if (missing.length === 0) return false

  console.error(`CI gate missing from ${label}:`)
  for (const { script, why } of missing) {
    // A neutralized step is the more likely of the two and reads as present to anyone skimming the
    // file, so it is named as such rather than reported as absent.
    const dead = neutralized.includes(script)
    console.error(
      `  npm run ${script} — ${dead ? 'present but behind `if:`/`continue-on-error`' : 'absent'}: ${why}`,
    )
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
  // Checked for whichever pipelines are present, including the split-repo shape where there is only
  // one — a workflow on the wrong runtime is wrong on its own, not only by comparison.
  const runtime = runtimeProblems(
    PACKAGE_JSON,
    checked.map(([{ label }, scan]) => ({ label, node: scan.node })),
  )
  if (runtime.length > 0) {
    console.error('CI runtime does not match the runtime this project declares:')
    for (const problem of runtime) console.error(problem)
  }
  const belowFloor = checked.map((args) => isBelowFloor(...args)).some(Boolean)
  if (!belowFloor && problems.length === 0 && runtime.length === 0) return
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

// Same scripts, different runtime, is still drift — and the invisible kind, because every gate
// passes in both files. Compared after the script sets, since a difference in what runs explains a
// difference in what it runs on, and reporting both at once reads as two unrelated faults.
if (standalone.node.join() !== monorepo.node.join()) {
  console.error('CI drift: the two frontend pipelines no longer run on the same Node version.')
  console.error(`  ${STANDALONE.label} : ${standalone.node.join(', ') || '(unpinned)'}`)
  console.error(`  ${MONOREPO.label}: ${monorepo.node.join(', ') || '(unpinned)'}`)
  console.error('Bring the two setup-node steps back in step; an unpinned one drifts on its own.')
  process.exit(1)
}

// The third way two pipelines diverge while running the same gate list: the same steps on
// different tooling. An action only one file uses is not drift - the monorepo shape has a docker
// job the split repo has no counterpart to - so only shared action names are compared.
const pins = pinProblems([
  { label: STANDALONE.label, pins: standalone.pins },
  { label: MONOREPO.label, pins: monorepo.pins },
])
if (pins.length > 0) {
  console.error('CI drift: the two frontend pipelines pin different action versions.')
  for (const problem of pins) console.error(problem)
  process.exit(1)
}

// Two ways a pipeline can be wrong that have nothing to do with the other one: an order the gates
// were not meant to run in, and a `paths:` filter that no longer matches the code they gate. The
// second is the quietest failure here — the workflow never starts, so nothing is red because
// nothing ran.
const triggers = [
  ...orderProblems(
    { label: STANDALONE.label, order: standalone.order },
    { label: MONOREPO.label, order: monorepo.order },
  ),
  ...pathsProblems(
    { label: MONOREPO.label, paths: monorepo.paths },
    { gated: 'frontend/', own: '.github/workflows/frontend-ci.yml' },
  ),
]
if (triggers.length > 0) {
  console.error('CI drift: the two frontend pipelines do not fire and run the same way.')
  for (const problem of triggers) console.error(problem)
  process.exit(1)
}

const on = standalone.node.length > 0 ? ` on Node ${[...new Set(standalone.node)].join(', ')}` : ''
console.log(`CI parity OK — both pipelines run${on}: ${monorepo.active.join(', ')}`)
