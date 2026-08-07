// The runtime half of the parity check's guard.
//
// Kept in its own file, and its own process, because the case file crossed the 200-line limit:
// splitting a suite by what it is ABOUT beats splitting it at whatever line the limit fell on.
// These cases are about the drift the script comparison cannot see - two pipelines running the
// same eight gates on two different Node versions, and a pipeline running on a runtime older than
// the one package.json declares. Both are invisible to a comparison of script names, and both end
// the same way: green here, broken for whoever pulls next.
import { expect, packageJson, workflowOn } from './ciParitySelftestHarness.mjs'
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

reportAndExit({
  subject: 'CI runtime',
  subjectIs: 'the parity check runtime comparison',
  script: 'check-ci-parity.mjs',
  tail: 'version drift, one side unpinned, agreement with engines, and a runtime below it',
})
