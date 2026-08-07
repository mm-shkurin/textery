import type { ProjectSummary } from '../../api/projectsApi'

// A sibling module to `projectFixtures.ts` for the same reason `projectSentinelFixtures.ts` is one:
// that file sits at 183 lines and the 200-line cap leaves no room for a set. The split is by
// concern — everything here exists to pin the card's PER-TYPE TINT, so each fixture differs from
// its neighbours in exactly one field, `documentType`. Every other fixture in this directory is a
// реферат or a доклад, which is why эссе and сочинение could share an accent unnoticed.

// Эссе is coral in Figma (frame 484:1104), not teal. It shipped teal, matching сочинение below —
// two types with the same badge fill, the same badge text colour and the same folder colour.
export const ESSAY_PROJECT: ProjectSummary = {
  kind: 'document',
  id: '31',
  title: 'Свобода и ответственность в жизни человека',
  preview: null,
  documentType: 'эссе',
  status: 'draft',
  retryable: false,
  createdAt: '2026-07-12T09:00:00Z',
  updatedAt: '2026-07-12T09:00:00Z',
}

// The type эссе was colliding WITH. Pinned alongside it rather than assumed: an accent table that
// swapped the two would satisfy a test naming only one of them.
export const SOCHINENIE_PROJECT: ProjectSummary = {
  kind: 'document',
  id: '33',
  title: 'Моё лето у бабушки: воспоминания детства',
  preview: null,
  documentType: 'сочинение',
  status: 'draft',
  retryable: false,
  createdAt: '2026-03-12T09:00:00Z',
  updatedAt: '2026-03-12T09:00:00Z',
}
