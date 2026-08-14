// What a document type IS, and how it crosses the wire. No Russian the user reads.
//
// This file used to carry both: the four ids sat in the same object as their card labels, their
// descriptions and six sentence builders, so the type the backend validates and the words on a
// button were one table. Renaming a card was a change to the domain; adding a language would have
// been a change to it too. The copy now lives in `copy/documentTypeCopy.ts`, importing from here.

export type DocumentType = 'doklad' | 'essay' | 'sochinenie' | 'referat'

// Every type the product knows, in the order screens render them — Реферат, Эссе, Доклад,
// Сочинение. The order is a product decision and this is the list every screen iterates, so it is
// stated once here instead of being sorted at each call site.
export const DOCUMENT_TYPE_IDS: readonly DocumentType[] = [
  'referat',
  'essay',
  'doklad',
  'sochinenie',
]

// Whether a type can be generated at all. Kept as data rather than deleted entries: it is the
// creation modal's «скоро» affordance, and the next type to be specced needs it again. All four
// are true — `SUPPORTED_DOCUMENT_TYPES` has admitted them since story 1, and since scenario 2.1
// each reaches the model through the domain's own `build_prompt`.
export const DOCUMENT_TYPE_AVAILABLE: Record<DocumentType, boolean> = {
  referat: true,
  essay: true,
  doklad: true,
  sochinenie: true,
}

export const DEFAULT_DOCUMENT_TYPE: DocumentType = 'doklad'

// The wire values the backend actually accepts — measured by curl against the live stack
// 2026-07-17, not read from a spec:
//   {"document_type":"doklad"} -> 422 {"error_code":"INVALID_DOCUMENT_TYPE"}
//   {"document_type":"доклад"} -> 201
//
// So the id above is an INTERNAL identifier (modal state, React keys) and this is the boundary
// translation. The frontend asked for Latin on the wire (docking-requirements.md) and the backend
// kept Cyrillic; mapping here was the stated fallback.
//
// Deliberately NOT derived from any display label, though today they hold the same four strings:
// a label belongs to the UI, and deriving the wire value from it would mean relabelling a card —
// 'Доклад' to 'Доклад (краткий)', say — silently breaks document creation, surfacing three layers
// away as a 422.
//
// `Record<DocumentType, string>` is exhaustive on purpose: adding a member to DocumentType without
// a wire value is a compile error here, in the file that has to know.
export const WIRE_DOCUMENT_TYPE: Record<DocumentType, string> = {
  doklad: 'доклад',
  essay: 'эссе',
  sochinenie: 'сочинение',
  referat: 'реферат',
}

// The inverse, for values coming BACK from the wire — the history list returns
// `document_type: "доклад"`, and reopening its rows needs the app's own DocumentType again.
// Derived rather than written out a second time: two hand-maintained tables are two chances to
// disagree, and the disagreement would be silent.
const APP_DOCUMENT_TYPE = Object.fromEntries(
  Object.entries(WIRE_DOCUMENT_TYPE).map(([app, wire]) => [wire, app]),
) as Record<string, DocumentType | undefined>

// Returns null for anything unrecognised rather than asserting. The server owns this value and can
// add a type before the client knows about it; crashing a whole history list over one unfamiliar
// row would be a worse answer than showing the row and declining to open it.
export function documentTypeFromWire(wire: string): DocumentType | null {
  return APP_DOCUMENT_TYPE[wire] ?? null
}
