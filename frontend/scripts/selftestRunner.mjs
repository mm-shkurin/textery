// The scaffolding shared by the two gate self-tests — check-nginx-503.selftest.mjs and
// check-ci-parity.selftest.mjs.
//
// Both drive a CI gate as a CHILD PROCESS against fixtures and judge it on two things only: the
// exit code, and whether the offending thing is actually quoted in the output. An exit 1 with an
// empty message would pass a bare code check while telling the reader nothing, so the quoting is
// asserted alongside the code every time — that pairing is the whole assertion vocabulary here.
//
// It lives in one file because the second self-test reimplemented the first one's plumbing line for
// line. What is NOT here is fixture building: what a conf directory or a pair of fixture workflows
// looks like is the part each self-test has to own, and reading it should not require this file.
import { execFileSync } from 'node:child_process'

// A gate that fails does so by exiting non-zero, which execFileSync raises — so the throw is the
// normal path, not an error, and both streams are merged because gates write their findings to
// stderr and their OK line to stdout. Cases quote against one string rather than picking a stream.
export function runNodeScript(script, flags) {
  try {
    const stdout = execFileSync(process.execPath, [script, ...flags], {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'pipe'],
    })
    return { code: 0, output: stdout }
  } catch (error) {
    // A non-numeric status means the child never ran to a verdict — ENOENT, EMFILE under a few
    // dozen spawns, a killed process. Reporting that as `expected exit 1, got undefined` dresses an
    // environment fault as a gate defect, under a banner that tells the reader not to relax the
    // cases; the predictable response to a gate that fails for reasons nobody can reproduce is to
    // unhook it. So it is named as what it is.
    if (typeof error.status !== 'number') {
      console.error(`self-test harness fault: ${script} could not be run — ${error.message}`)
      console.error('This is the harness failing, not the gate. Nothing about the gate was proven.')
      process.exit(1)
    }
    return { code: error.status, output: `${error.stdout ?? ''}${error.stderr ?? ''}` }
  }
}

const failures = []
let casesRun = 0

// Failures are collected rather than thrown so one run reports every broken case. A self-test that
// stops at the first one turns "the gate is wrong in four ways" into four separate debugging trips.
export function check(what, condition, detail) {
  if (condition) return
  failures.push(`  ${what}\n     ${detail}`)
}

// For the cases that assert something about a run without going through expectVerdict.
export function countCase() {
  casesRun += 1
}

export function checkVerdict({ what, result, code, quotes = [] }) {
  countCase()
  check(
    what,
    result.code === code,
    `expected exit ${code}, got ${result.code}. Output:\n${result.output}`,
  )
  for (const quote of quotes) {
    check(
      `${what} — quotes ${JSON.stringify(quote)}`,
      result.output.includes(quote),
      `that string is absent from the output:\n${result.output}`,
    )
  }
}

// Counted, never hardcoded: a printed constant is how these suites would acquire the disease they
// were written to cure — a case deleted while debugging, and a PASS line that reads identically.
export function reportAndExit({ subject, subjectIs, script, tail }) {
  if (failures.length > 0) {
    console.error(`${subject} self-test: ${subjectIs} does not behave as its callers assume.`)
    console.error(failures.join('\n'))
    console.error(`Fix ${script} — do not relax these cases to make this pass.`)
    process.exit(1)
  }

  console.log(`${subject} self-test OK — ${casesRun} cases: ${tail}`)
}
