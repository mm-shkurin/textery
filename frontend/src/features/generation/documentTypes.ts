export type DocumentType = 'doklad' | 'essay' | 'sochinenie' | 'referat'

export interface DocumentTypeOption {
  id: DocumentType
  name: string
  available: boolean
}

export const DOCUMENT_TYPES: DocumentTypeOption[] = [
  { id: 'doklad', name: 'Доклад', available: true },
  { id: 'essay', name: 'Эссе', available: false },
  { id: 'sochinenie', name: 'Сочинение', available: false },
  { id: 'referat', name: 'Реферат', available: false },
]

export const DEFAULT_DOCUMENT_TYPE: DocumentType = 'doklad'

// Display labels, derived from DOCUMENT_TYPES rather than written out again. App.tsx used to
// carry its own copy of these four strings — a second hand-maintained table of the same facts,
// which is the arrangement this file already warns against for the wire values below. Renaming
// a card in the modal now renames it in the editor's breadcrumb, because there is one source.
export const DOCUMENT_TYPE_LABELS = Object.fromEntries(
  DOCUMENT_TYPES.map((t) => [t.id, t.name]),
) as Record<DocumentType, string>

// The wire values the backend actually accepts — measured by curl against the live stack
// 2026-07-17, not read from a spec:
//   {"document_type":"doklad"} -> 422 {"error_code":"INVALID_DOCUMENT_TYPE"}
//   {"document_type":"доклад"} -> 201
//
// So `id` above is an INTERNAL identifier (mode-modal state, React keys) and this is the
// boundary translation. The frontend asked for Latin on the wire (docking-requirements.md) and
// the backend kept Cyrillic; mapping here was the stated fallback.
//
// Deliberately NOT `name.toLowerCase()`, though it would produce the same four strings today:
// `name` is a display label and belongs to the UI. Deriving the wire value from it would mean
// that relabelling a card in the modal — 'Доклад' to 'Доклад (краткий)', say — silently breaks
// document creation, with the failure surfacing three layers away as a 422.
//
// `Record<DocumentType, string>` is exhaustive on purpose: adding a member to DocumentType
// without a wire value is a compile error here, in the file that has to know.
export const WIRE_DOCUMENT_TYPE: Record<DocumentType, string> = {
  doklad: 'доклад',
  essay: 'эссе',
  sochinenie: 'сочинение',
  referat: 'реферат',
}

// The inverse, for values coming BACK from the wire — the history list returns
// `document_type: "доклад"`, and reopening its rows needs the app's own DocumentType again.
// Derived from the map above rather than written out a second time: two hand-maintained tables
// are two chances to disagree, and the disagreement would be silent.
const APP_DOCUMENT_TYPE = Object.fromEntries(
  Object.entries(WIRE_DOCUMENT_TYPE).map(([app, wire]) => [wire, app]),
) as Record<string, DocumentType | undefined>

// Returns null for anything unrecognised rather than asserting. The server owns this value and
// can add a type before the client knows about it; crashing a whole history list over one
// unfamiliar row would be a worse answer than showing the row and declining to open it.
export function documentTypeFromWire(wire: string): DocumentType | null {
  return APP_DOCUMENT_TYPE[wire] ?? null
}
