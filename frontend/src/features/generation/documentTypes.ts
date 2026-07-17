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
