import { vi } from 'vitest'

// Shared wire fixtures and transport stub for the «Мои проекты» api tests. One definition each,
// because both suites in this directory read the same endpoint: a second hand-copied literal drifts
// the moment the contract gains a field, and a drifted fixture makes a contract test fail for a
// reason it does not name.

// A generation, not a document: it is the arm that carries the fields a document-shaped fixture
// would leave untested — `can_repeat: true`, and a `preview` that is null while the title is
// present. Both are server-computed and neither may be re-derived on this side.
//
// `document_type` is Cyrillic because that is what the wire actually carries: the frontend asked
// for Latin ids and the backend kept Cyrillic, so `shared/documentTypes.ts` translates at the
// boundary (`WIRE_DOCUMENT_TYPE`) and `ProjectCard` calls `documentTypeLabelFromWire`. The mapping
// under test is a pass-through on this field, so no assertion can catch a wrong vocabulary — which
// is exactly why the fixture has to be right: it is what green's implementation, the MSW handlers,
// and scenario 1.5's unknown-type arm all get read from.
export const PROJECT_WIRE = {
  kind: 'generation',
  id: '9f1c2b74-0000-4000-8000-00000000abcd',
  title: 'Квантовые вычисления',
  preview: null,
  document_type: 'реферат',
  status: 'failed',
  can_repeat: true,
  created_at: '2026-07-15T09:00:00Z',
  updated_at: '2026-07-15T09:00:00Z',
}

// The same item as the break would actually arrive: the required snake_case `updated_at` is gone
// and a camelCase `updatedAt` carries the value instead — the single most likely way this contract
// drifts, since it is what a serializer switched to camelCase emits.
//
// DERIVED from `PROJECT_WIRE` rather than written out again, and that is the assertion: the claim
// the contract test rests on is «every other field is valid, so nothing but the missing required
// key can be what fails». A copied literal only makes that claim; destructuring makes it true, and
// keeps it true when the contract adds a field.
const { updated_at, ...EVERY_OTHER_FIELD } = PROJECT_WIRE

export const PROJECT_WIRE_WITHOUT_UPDATED_AT = { ...EVERY_OTHER_FIELD, updatedAt: updated_at }

// The settlement of a promise, captured rather than asserted on directly. Shared for the same
// reason as the wire fixtures above: both fail-closed suites in this directory need it, and a
// second hand-copied definition drifts the moment the shape changes.
export type Settled = { rejected: false; value: unknown } | { rejected: true; error: unknown }

// Capture the settlement rather than `.rejects.toThrow()`: that would pass on ANY thrown value —
// including `send`'s generic 'Не удалось загрузить проекты' transport fallback and the engine's own
// `TypeError`, the two outcomes these suites most need to tell apart from a real mapper guard.
// Comparing the whole settlement in one `toEqual` then pins outcome, error type and message
// together: an `Error` and a plain object carrying the same `message` are not equal, and neither is
// a different message.
export async function settle(promise: Promise<unknown>): Promise<Settled> {
  return promise.then(
    (value) => ({ rejected: false as const, value }),
    (error: unknown) => ({ rejected: true as const, error }),
  )
}

// The transport stub every api test here shares. `GET /api/v1/projects` does not exist on the
// backend yet, so nothing in this directory may reach a real server. Returns the mock so the caller
// can pin how many times it was called and with what.
export function stubFetchJson(body: unknown): ReturnType<typeof vi.fn> {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => body,
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}
