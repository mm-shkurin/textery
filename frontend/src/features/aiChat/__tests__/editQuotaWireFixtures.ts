// Feature-level test fixtures for the edit-quota contract — the ones BOTH the api layer
// (`api/__tests__/editQuotaApi.test.ts`) and the component layer
// (`components/__tests__/DocumentEditorPage.overQuota.test.tsx`) assert against.
//
// It lives here rather than in `api/__tests__/editorDocumentApiFixtures.ts` because that file is
// api-only: a component test importing across into another layer's `__tests__` would be the
// coupling stated as a comment again, just spelled with a longer path. `aiChat/__tests__/` is the
// one directory both layers are below.

// A NON-CANONICAL instant on purpose: a Moscow offset rather than `Z`, and no fractional seconds.
// `data-resets-at` must carry the wire string the API returned, byte for byte, and any
// `new Date(...)`/`toISOString()` anywhere on the path from `loadEditQuota`'s mapping to the
// attribute rewrites this to '2026-08-10T21:00:00.000Z' — which is what makes both layers fail
// loudly instead of the Selenium layer discovering the fragility across two serializations.
//
// ONE constant, imported by both layers, because the api test's byte-equality claim and the
// component test's `data-resets-at` claim are the SAME claim about the same instant. Two hand-kept
// copies said so in a comment while nothing stopped a well-meaning tidy-up from canonicalising one
// of them — leaving both files green and the round-trip trap silently deleted on one side.
export const RESETS_AT_WIRE = '2026-08-11T00:00:00+03:00'
