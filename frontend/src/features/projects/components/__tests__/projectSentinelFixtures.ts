import type { ProjectSummary } from '../../api/projectsApi'

// A sibling module to `projectFixtures.ts` rather than two more exports appended to it: that file
// is at 183 lines and these two fixtures carry the reasoning below, which would put it past the
// 200-line limit. The split is by concern, not by line count — everything here is a SENTINEL
// timestamp, a value the backend writes to mean "no date" while sending a syntactically perfect
// ISO string, which is a different failure class from `projectFixtures.ts`'s malformed/absent trio.
//
// What makes the pair below distinct from every bad-date fixture already pinned: they are valid
// strings AND valid Dates. `typeof iso !== 'string'` passes them, `Number.isNaN(date.getTime())`
// passes them, and the year branch then renders them in full. Every guard `formatCardDate` ships
// today is a guard on the SHAPE of the input; a sentinel has the right shape and a nonsense value,
// so only a bounded plausible-year check can reject it.

// `0001-01-01T00:00:00Z` — what `LocalDate.MIN`, `datetime.min` and `DateTime.MinValue` serialize
// to when a nullable column is mapped through a non-nullable domain field. Renders '1 января 1'.
export const MIN_SENTINEL_DATE_PROJECT: ProjectSummary = {
  kind: 'document',
  id: '23',
  title: 'Проект с минимальной датой',
  preview: null,
  documentType: 'реферат',
  status: 'draft',
  retryable: false,
  createdAt: '2026-07-15T09:00:00Z',
  updatedAt: '0001-01-01T00:00:00Z',
}

// `9999-12-31T23:59:59Z` — the max-value sentinel (`LocalDate.MAX`, Postgres `infinity` clamped on
// serialization). Renders '1 января 10000' in Europe/Moscow, where the +3 offset rolls the last
// second of 9999 into a five-digit year the mockup has no format for.
//
// The worse of the two, and the reason this fixture is not redundant with its sibling: story 1.4's
// «Недавние проекты» rail sorts on `updated_at` descending, so a single row carrying this sentinel
// takes the top slot permanently and the user's genuinely newest work never surfaces. A guard that
// only rejects implausibly OLD years leaves that arm intact — which is why the two are pinned as
// separate tests rather than one.
export const MAX_SENTINEL_DATE_PROJECT: ProjectSummary = {
  kind: 'document',
  id: '25',
  title: 'Проект с максимальной датой',
  preview: null,
  documentType: 'реферат',
  status: 'draft',
  retryable: false,
  createdAt: '2026-07-15T09:00:00Z',
  updatedAt: '9999-12-31T23:59:59Z',
}
