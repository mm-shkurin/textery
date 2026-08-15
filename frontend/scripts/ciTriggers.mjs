// What makes a pipeline RUN at all, and what makes two of them run their gates in the same order.
//
// Everything else the parity check compares is about a pipeline that fires. These two are about the
// ways it silently does not, or does something subtly different while looking identical.

// `paths:` entries under `on:`. Read as a flat list rather than per-trigger: `push` and
// `pull_request` carry the same filter here, and a difference between those two is a different
// question from the one below.
const PATHS_BLOCK = /(?:^|\n)\s*paths:\s*\n((?:\s*-\s*'?"?[^\n'"]+'?"?\n?)+)/g

export function triggerPaths(contents) {
  const entries = []
  for (const [, block] of contents.matchAll(PATHS_BLOCK)) {
    for (const line of block.split('\n')) {
      const match = /^\s*-\s*'?"?([^'"\s]+)'?"?\s*$/.exec(line)
      if (match) entries.push(match[1])
    }
  }
  return [...new Set(entries)].sort()
}

// A `paths:` filter that no longer matches the code it gates is the quietest failure a pipeline
// has. Nothing goes red — the workflow simply never starts, the commit lands with no checks, and
// the branch protection UI shows no failing job because there is no job. It is one renamed
// directory away at all times, and the only thing that would notice is this.
//
// Two things must be covered: the directory the gates run over, and the workflow's OWN file. The
// second is not pedantry — a workflow that does not re-run when it is edited cannot be fixed by
// editing it, and the first sign is a "fix" that changes nothing.
//
// A pipeline with NO `paths:` is not checked: that is the split-repo shape, where the whole
// repository is the gated directory and a filter would be the mistake.
export function pathsProblems({ label, paths }, { gated, own }) {
  if (paths.length === 0) return []

  const covers = (target) =>
    paths.some((pattern) => target === pattern || target.startsWith(pattern.replace(/\*+$/, '')))

  return [
    ...(covers(gated) ? [] : [`  ${label} does not fire on changes under ${gated}.`]),
    ...(covers(own) ? [] : [`  ${label} does not fire when it is edited itself (${own}).`]),
  ].map(
    (problem) =>
      `${problem}\n    Its paths: filter is ${paths.join(', ')} — a pipeline that does not start is not a pipeline that passed.`,
  )
}

// Same gates, same runtime, different sequence. Not cosmetic: the gates are ordered cheapest-first
// on purpose, so a typo fails in seconds rather than after a four-minute test run, and one pipeline
// reporting a different failure than the other for the same commit is how "it passes for me" starts.
// Compared over the SHARED scripts only, so a gate legitimately present in one file does not read
// as a reordering of the others.
export function orderProblems(first, second) {
  const shared = first.order.filter((script) => second.order.includes(script))
  const counterpart = second.order.filter((script) => first.order.includes(script))
  if (shared.join() === counterpart.join()) return []

  return [
    `  ${first.label} : ${shared.join(' -> ')}`,
    `  ${second.label}: ${counterpart.join(' -> ')}`,
    '    Same gates, different sequence. They are ordered cheapest-first so a typo fails in seconds;',
    '    two pipelines reporting different first failures for one commit is how "green for me" starts.',
  ]
}
