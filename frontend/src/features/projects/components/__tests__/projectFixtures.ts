import type { ProjectSummary } from '../../api/projectsApi'

// A document and a generation deliberately seeded with THE SAME id. That is not a contrived
// fixture: the two arms of the merged feed come from different tables, so their ids can collide,
// and a component keying rows on `key={id}` would render one node for the pair. The story pins
// the key as `(kind, id)`; two cards on screen is what proves it.
export const DOCUMENT: ProjectSummary = {
  kind: 'document',
  id: '1',
  title: 'Влияние искусственного интеллекта на рынок труда',
  preview: null,
  documentType: 'реферат',
  status: 'draft',
  retryable: false,
  createdAt: '2026-07-15T09:00:00Z',
  updatedAt: '2026-07-15T09:00:00Z',
}

export const GENERATION: ProjectSummary = {
  kind: 'generation',
  id: '1',
  title: 'Открытие кофейни в спальном районе',
  preview: null,
  documentType: 'доклад',
  status: 'failed',
  retryable: true,
  createdAt: '2026-06-02T09:00:00Z',
  updatedAt: '2026-06-02T09:00:00Z',
}

// A wire `document_type` this client has never heard of. The server owns that vocabulary and can
// add a member before the frontend learns it, so `documentTypeFromWire` returns null by design —
// and every other fixture in this file is a KNOWN type, which is why the card's accent fallback
// has never actually rendered.
export const UNKNOWN_TYPE_PROJECT: ProjectSummary = {
  kind: 'document',
  id: '7',
  title: 'Курсовая работа по микроэкономике',
  preview: null,
  documentType: 'курсовая',
  status: 'draft',
  retryable: false,
  createdAt: '2026-07-15T09:00:00Z',
  updatedAt: '2026-07-15T09:00:00Z',
}

// Dated in a year that is not the pinned "now". Every other fixture in this file is 2026, which is
// why the card's with-the-year date format has never once rendered. The literal is lifted from the
// mockup (mockups/desktop/01-projects-grid.html: `<div class="date">2 сентября 2025</div>`) so the
// assertion is anchored to the design, not to whatever the formatter happens to emit.
export const OLDER_YEAR_PROJECT: ProjectSummary = {
  kind: 'document',
  id: '9',
  title: 'Экономика замкнутого цикла',
  preview: null,
  documentType: 'реферат',
  status: 'draft',
  retryable: false,
  createdAt: '2025-09-02T09:00:00Z',
  updatedAt: '2025-09-02T09:00:00Z',
}

// A SECOND older-year fixture, and the reason it is not redundant with the one above: one
// assertion pins one month and one year, so the cheapest way to satisfy it is a hand-rolled
// Russian genitive month table — eleven of whose entries no test would ever read. This fixture
// picks a different month AND a different year, both lifted from the same mockup
// (mockups/desktop/01-projects-grid.html: `<div class="date">16 декабря 2024</div>`), so the
// table has to be right twice before it is cheaper than keeping `toLocaleDateString`.
export const SECOND_OLDER_YEAR_PROJECT: ProjectSummary = {
  kind: 'document',
  id: '11',
  title: 'История отечественной архитектуры',
  preview: null,
  documentType: 'реферат',
  status: 'draft',
  retryable: false,
  createdAt: '2024-12-16T12:00:00Z',
  updatedAt: '2024-12-16T12:00:00Z',
}

// The only fixture in this file whose `createdAt` and `updatedAt` are NOT the same string. Every
// other one aliases them, which means the card could be reading `createdAt` and the whole suite
// would stay green. `12_MyProjects.md` makes the two equal only at birth ("its `updated_at` equal
// to its `created_at`") and names `updated_at` a sort key — they diverge on the first save, and
// the feed's job is telling recently-touched work apart. The two dates are chosen to format
// differently: the creation renders with a year ('5 марта 2024'), the edit without one
// ('15 июля'), so a card reading the wrong field cannot accidentally satisfy the assertion.
export const EDITED_LONG_AFTER_CREATION_PROJECT: ProjectSummary = {
  kind: 'document',
  id: '13',
  title: 'Цифровизация городского транспорта',
  preview: null,
  documentType: 'реферат',
  status: 'draft',
  retryable: false,
  createdAt: '2024-03-05T12:00:00Z',
  updatedAt: '2026-07-15T12:00:00Z',
}

// Two fixtures for two ways the same field goes bad, because ONE `isNaN` guard fixes only the
// first. `projectsApi.ts` maps `item.updated_at` straight through with no validation, against an
// endpoint the backend has not built (`endpoints.md`) — so what arrives is whatever the server
// eventually sends, and `ProjectSummary.updatedAt: string` is a compile-time claim about a runtime
// JSON body, which is why both casts below are `as unknown as string` rather than fixture sloppiness.
//
// Malformed: `new Date('30 февраля, наверное')` is an Invalid Date, `getFullYear()` is NaN, and
// `NaN !== currentYear` is TRUE — so the card takes the year-SHOWING branch and concatenates two
// failure tokens into 'Invalid Date NaN'. Verified in this repo's node.
export const UNPARSEABLE_DATE_PROJECT: ProjectSummary = {
  kind: 'document',
  id: '15',
  title: 'Проект с испорченной датой',
  preview: null,
  documentType: 'реферат',
  status: 'draft',
  retryable: false,
  createdAt: '2026-07-15T09:00:00Z',
  updatedAt: '30 февраля, наверное' as unknown as string,
}

// Missing: `new Date(null)` is the epoch — a perfectly VALID Date — so it renders '1 января 1970',
// which reads to the user as a real edit date rather than as an absent one. That is the worse half
// of the pair and the reason it is pinned here: a green fix that only checks `isNaN(getTime())`
// leaves this card lying. Verified in this repo's node.
export const MISSING_DATE_PROJECT: ProjectSummary = {
  kind: 'document',
  id: '17',
  title: 'Проект без даты',
  preview: null,
  documentType: 'реферат',
  status: 'draft',
  retryable: false,
  createdAt: '2026-07-15T09:00:00Z',
  updatedAt: null as unknown as string,
}

// A NUMBER where the wire contract promises an ISO string — an epoch-millis body, the single most
// common way a JSON timestamp arrives wrong, and the one shape neither fixture above covers.
// `new Date(1755000000)` is valid, non-NaN and non-null; it reads '21 января 1970'. So it is caught
// by neither an `isNaN` check nor a null check — only by the `typeof iso !== 'string'` INPUT guard,
// which shipped in the same green as the two fixtures above while nothing asserted this arm of it.
// Same `as unknown as string` cast as its two siblings, for the same reason: `updatedAt: string` is
// a compile-time claim about a runtime JSON body from an endpoint the backend has not built.
export const NUMERIC_DATE_PROJECT: ProjectSummary = {
  kind: 'document',
  id: '19',
  title: 'Проект с числовой датой',
  preview: null,
  documentType: 'реферат',
  status: 'draft',
  retryable: false,
  createdAt: '2026-07-15T09:00:00Z',
  updatedAt: 1755000000 as unknown as string,
}

// The CONVERSE of every fixture above: a genuine, well-formed, perfectly usable timestamp that
// happens to be the epoch. It must render as a real date — the user really did edit this on
// 1 января 1970 as far as the card is concerned, and declining to say so would be the same class of
// lie as rendering '1 января 1970' for an absent one, in the other direction.
//
// The reason it is pinned at all: appending `|| date.getTime() === 0` to `formatCardDate`'s
// validity guard passes all nine tests that existed before this fixture, while blanking this card.
// That mutation is an epoch-VALUE guard wearing an input guard's clothes, and it is exactly the fix
// the previous green's comment says it refused to write — with nothing in the suite enforcing the
// refusal. This fixture is the enforcement.
//
// The instant is `T00:00:00Z` and cannot be moved: only the exact epoch triggers the mutation, so
// unlike every other fixture here it cannot be nudged to midday UTC. That makes the assertion
// timezone-dependent — west of UTC this date renders '31 декабря 1969', verified by running the
// suite under America/New_York, where it was the ONLY failure. The zone is therefore pinned to
// Europe/Moscow in `vite.config.ts` (`test.env.TZ`); this fixture is why that pin landed here
// rather than in the later step that had queued it.
export const EPOCH_DATE_PROJECT: ProjectSummary = {
  kind: 'document',
  id: '21',
  title: 'Проект из 1970 года',
  preview: null,
  documentType: 'реферат',
  status: 'draft',
  retryable: false,
  createdAt: '2026-07-15T09:00:00Z',
  updatedAt: '1970-01-01T00:00:00Z',
}
