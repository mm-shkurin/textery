// Sameness is not presence: two identical pipelines that run NOTHING satisfy the comparison below,
// and so does deleting one step from both files in the same commit. That is the shape of the
// failure this file exists to prevent, one level up — every gate here is a step someone under
// release pressure can remove, and the only thing that noticed would be this comparison, which
// removal keeps green.
//
// So the gates are named. Each entry says what is lost when it goes, because a bare list gets
// pruned as clutter and a reason does not. `mustContain` pins the part of a composite body the
// reason depends on — a name in a workflow says nothing about what the script still does.
export const REQUIRED = [
  {
    script: 'typecheck',
    why: 'tsc -b; without it a broken build reaches main invisibly (vitest strips types)',
  },
  {
    script: 'test:coverage',
    why: 'the suite AND the per-file coverage floors, which only fire under --coverage',
    mustContain: ['--coverage', 'check-per-file-coverage.mjs'],
  },
  { script: 'build', why: 'the one step that proves the app still compiles and bundles' },
  { script: 'lint', why: 'oxlint at --max-warnings=0', mustContain: ['--max-warnings=0'] },
  { script: 'format:check', why: 'a .prettierrc nobody runs is a preference, not a convention' },
  {
    script: 'audit',
    why: 'every production advisory, against the dated exception ledger — no severity threshold',
    mustContain: ['check-audit.selftest.mjs', 'check-audit.mjs'],
  },
  {
    script: 'ci:parity',
    why: 'this check; a pipeline that drops it can then drift freely',
    mustContain: [
      'check-ci-parity.selftest.mjs',
      'check-ci-parity.runtime.selftest.mjs',
      'check-ci-parity.mjs',
    ],
  },
  {
    script: 'check:ingress',
    why: 'the nginx 503 guard behind mayHaveLandedServerSide — see that predicate',
    mustContain: [
      'check-nginx-503.selftest.mjs',
      'check-nginx-503.premise.selftest.mjs',
      'check-nginx-503.mjs',
    ],
  },
]
