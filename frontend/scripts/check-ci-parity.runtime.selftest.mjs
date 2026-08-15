// The runtime half of the parity check's guard.
//
// Kept in its own file, and its own process, because the case file crossed the 200-line limit:
// splitting a suite by what it is ABOUT beats splitting it at whatever line the limit fell on.
// These cases are about the drift the script comparison cannot see: two pipelines running the same
// eight gates on two different Node versions, a pipeline running on a runtime older than the one
// package.json declares, and the two files pinning different versions of the same action. All
// three are invisible to a comparison of script names, and all three end the same way: green here,
// broken for whoever pulls next.
import {
  ALL,
  expect,
  packageJson,
  workflowFiltering,
  workflowOn,
} from './ciParitySelftestHarness.mjs'
import { reportAndExit } from './selftestRunner.mjs'

// The blind spot the script comparison leaves open: both files run every gate, on two different
// runtimes. Nothing about the set of scripts differs, so only a runtime comparison can see it.
expect({
  what: 'the same gates on two different Node versions fail as drift',
  raw: { standalone: workflowOn('20'), monorepo: workflowOn('22') },
  code: 1,
  quotes: ['no longer run on the same Node version', '20', '22'],
})
expect({
  what: 'one pipeline pinning a runtime and the other pinning none fails',
  raw: { standalone: workflowOn('20') },
  code: 1,
  quotes: ['(unpinned)'],
})
expect({
  what: 'both pipelines on the runtime package.json declares pass, and say so',
  raw: { standalone: workflowOn('20'), monorepo: workflowOn('20') },
  pkg: packageJson({}, { node: '>=20.19' }),
  code: 0,
  quotes: ['on Node 20'],
})
expect({
  what: 'a pipeline pinned below the declared engines fails',
  raw: { standalone: workflowOn('18'), monorepo: workflowOn('18') },
  pkg: packageJson({}, { node: '>=20.19' }),
  code: 1,
  quotes: ['runs Node 18, but package.json requires >=20.19'],
})
// The split-repo shape has nothing to compare against, so the engines check is the only thing
// standing between it and a runtime nobody chose.
expect({
  what: 'the split-repo shape still fails a runtime below engines',
  monorepo: null,
  raw: { standalone: workflowOn('18') },
  pkg: packageJson({}, { node: '>=20.19' }),
  code: 1,
  quotes: ['runs Node 18'],
})

// Action pins, the third invisible divergence: identical steps, different tooling running them.
expect({
  what: 'the two pipelines pinning different versions of the same action fail',
  raw: {
    standalone: workflowOn('20', ALL, ['actions/checkout@v4', 'actions/setup-node@v4']),
    monorepo: workflowOn('20', ALL, ['actions/checkout@v5', 'actions/setup-node@v4']),
  },
  code: 1,
  quotes: ['pin different action versions', 'actions/checkout'],
})

// The case that must NOT fail, and the reason the comparison is per shared action name rather than
// per action set: the monorepo shape has a docker job the split repo has no counterpart to.
expect({
  what: 'an action only one pipeline uses is not drift',
  raw: {
    standalone: workflowOn('20', ALL, ['actions/setup-node@v4']),
    monorepo: workflowOn('20', ALL, ['actions/setup-node@v4', 'docker/build-push-action@v6']),
  },
  code: 0,
  quotes: ['CI parity OK'],
})

// The same defect one scope down, and what a half-finished bump looks like from outside.
expect({
  what: 'one file pinning an action to two different versions fails',
  raw: {
    standalone: workflowOn('20', ALL, ['actions/checkout@v4', 'actions/checkout@v5']),
    monorepo: workflowOn('20', ALL, ['actions/checkout@v4', 'actions/checkout@v5']),
  },
  code: 1,
  quotes: ['pinned to v4 and v5 within one file'],
})

// Same gates, same runtime, different sequence. Ordered cheapest-first on purpose, and two
// pipelines reporting different first failures for one commit is how "green for me" starts.
expect({
  what: 'the same gates in a different order fail',
  standalone: ALL,
  monorepo: [...ALL].reverse(),
  code: 1,
  quotes: ['do not fire and run the same way', 'different sequence'],
})

// The quietest failure a pipeline has: the filter stops matching, the workflow never starts, and
// nothing is red because nothing ran.
expect({
  what: 'a monorepo paths filter that misses the gated directory fails',
  raw: { monorepo: workflowFiltering(['backend/**', '.github/workflows/frontend-ci.yml']) },
  code: 1,
  quotes: ['does not fire on changes under frontend/'],
})

// A workflow that does not re-run when it is edited cannot be fixed by editing it, and the first
// symptom is a "fix" that changes nothing.
expect({
  what: 'a paths filter that omits the workflow itself fails',
  raw: { monorepo: workflowFiltering(['frontend/**']) },
  code: 1,
  quotes: ['does not fire when it is edited itself'],
})

// The shape that must NOT fail: no `on:` block at all is the split repository, where the whole
// checkout is the gated directory and a filter would be the mistake.
expect({
  what: 'a pipeline with no paths filter at all is not a trigger problem',
  code: 0,
  quotes: ['CI parity OK'],
})

reportAndExit({
  subject: 'CI runtime, action pins and triggers',
  subjectIs: 'the parity check runtime comparison',
  script: 'check-ci-parity.mjs',
  tail: 'runtime drift and engines, three action-pin cases, step order, and three paths-filter cases',
})
