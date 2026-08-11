import { expect } from 'vitest'

/**
 * Story 10, UI scenario 1.1 — the comparator every probe case in
 * `fixtureUsage.patterns.test.ts` routes through.
 *
 * The probe array is built FROM the two expected lists, so neither side of the comparison is a
 * second spelling of the other. A pattern that changes its mind about one probe moves that probe
 * between the two halves of the received value and the named line prints in the diff.
 *
 * WHY THIS IS A MODULE AND NOT A LOCAL CONST. It has two callers with two different subjects:
 * `fixtureUsage.patterns.test.ts` uses it to state what the four patterns MEAN, and
 * `fixtureUsage.partitionControl.test.ts` uses it as the SUBJECT — proving this body consults
 * `pattern` at all, which nothing in the first file can prove. Those two arguments were sharing one
 * file at the 200-line cap, which is what blocked the length pin the first file now carries. The
 * split is on the seam between "the patterns are narrow" and "the comparator is not tautological";
 * read the control file's header before simplifying anything below.
 */
export const expectPartition = (
  pattern: RegExp,
  accepted: readonly string[],
  rejected: readonly string[],
): void => {
  const probes = [...accepted, ...rejected]
  expect({
    accepted: probes.filter((probe) => pattern.test(probe)),
    rejected: probes.filter((probe) => !pattern.test(probe)),
  }).toStrictEqual({ accepted, rejected })
}
