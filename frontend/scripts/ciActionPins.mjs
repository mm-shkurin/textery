// Action pins - `uses: owner/action@ref` - read out of a workflow and compared between the two
// pipelines. Split from ciPipelineScan.mjs, which reached the 200-line limit; this is a whole
// second question about a workflow (what TOOLING runs it) rather than more of the first one
// (which gates run), so it is the seam that was already there.
// `uses: owner/action@ref`, as a name -> set of refs. The version is the half that drifts: one
// pipeline moves to actions/checkout@v5 and the other stays on v4, and from then on the two are
// running different tooling while every gate still passes in both.
const USES_ACTION = /(?:^|\n)\s*-?\s*uses:\s*([\w.-]+\/[\w.-]+)@(\S+)/g

export function actionPins(contents) {
  const pins = new Map()
  for (const [, name, ref] of contents.matchAll(USES_ACTION)) {
    if (!pins.has(name)) pins.set(name, new Set())
    pins.get(name).add(ref)
  }
  return [...pins].map(([name, refs]) => ({ name, refs: [...refs].sort() }))
}

// Compared per ACTION NAME, over the names both files use. An action only one of them has is not
// drift: the monorepo shape has a docker job that the split repo has no equivalent of, and
// demanding identical action sets would fail on a difference that is the whole reason there are
// two files. What must agree is the version of anything they share.
//
// A single file pinning one action to two different refs is reported too - it is the same defect
// one scope down, and it is how a half-finished bump looks.
export function pinProblems(pipelines) {
  const problems = []
  const [first, second] = pipelines

  for (const { name, refs } of [...first.pins, ...second.pins]) {
    if (refs.length > 1) {
      problems.push(
        `  ${name} is pinned to ${refs.join(' and ')} within one file — finish the bump or revert it.`,
      )
    }
  }

  for (const { name, refs } of first.pins) {
    const counterpart = second.pins.find((pin) => pin.name === name)
    if (counterpart && counterpart.refs.join() !== refs.join()) {
      problems.push(
        `  ${name}: ${first.label} pins @${refs.join(',')}, ${second.label} pins @${counterpart.refs.join(',')}.\n` +
          '    Bump both; a pipeline left behind runs different tooling on the same commit.',
      )
    }
  }

  return problems
}
