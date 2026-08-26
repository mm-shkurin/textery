// Everything a user reads about a document type: card labels, descriptions, and the phrases the
// type has to be declined into.
//
// Separated from `documentTypes.ts` because those are different things with different owners. The
// domain file answers "what types exist and what does the server call them"; this one answers
// "what do we say to a person" — and Russian makes that a real body of knowledge: a label cannot
// be concatenated into a sentence and stay grammatical, so the type needs a genitive, an
// accusative and an agreeing possessive before a heading can be written.

import {
  DOCUMENT_TYPE_AVAILABLE,
  DOCUMENT_TYPE_IDS,
  documentTypeFromWire,
  type DocumentType,
} from '../domain/documentTypes'

export interface DocumentTypeOption {
  id: DocumentType
  name: string
  available: boolean
  // The line under the name on the creation modal's card — what the type IS, in the words the
  // Figma frame «Мои проекты - Создать проект» (788:5094) uses. It sits beside `name` because it
  // is copy, and the modal is not the only screen that will want to say what a доклад is.
  description: string
}

export const DOCUMENT_TYPE_LABELS: Record<DocumentType, string> = {
  referat: 'Реферат',
  essay: 'Эссе',
  doklad: 'Доклад',
  sochinenie: 'Сочинение',
}

const DOCUMENT_TYPE_DESCRIPTIONS: Record<DocumentType, string> = {
  referat: 'Изложение темы с выводами',
  essay: 'Личный взгляд на проблему',
  doklad: 'Текст для устного выступления',
  sochinenie: 'Рассуждение на тему с позицией',
}

// The list every screen renders, assembled from the domain's order and availability plus the copy
// above. One source: renaming a card in the modal renames it in the editor's breadcrumb.
export const DOCUMENT_TYPES: DocumentTypeOption[] = DOCUMENT_TYPE_IDS.map((id) => ({
  id,
  name: DOCUMENT_TYPE_LABELS[id],
  available: DOCUMENT_TYPE_AVAILABLE[id],
  description: DOCUMENT_TYPE_DESCRIPTIONS[id],
}))

// Genitive forms, for copy that names the type inside a phrase — 'Тема доклада', not 'Тема
// Доклад'. The composer's field heading was a hardcoded 'Тема доклада' precisely because
// interpolating the label produces nonsense for every other type.
//
// Hand-written and exhaustive: this cannot be derived by any rule (доклад -> доклада, эссе ->
// эссе, сочинение -> сочинения), and adding a member to DocumentType without a form here is a
// compile error in the file that has to know.
export const DOCUMENT_TYPE_GENITIVE: Record<DocumentType, string> = {
  doklad: 'доклада',
  essay: 'эссе',
  sochinenie: 'сочинения',
  referat: 'реферата',
}

// Lowercase nominative/accusative, for copy that names the type as the object of a verb — 'Готовим
// ваш доклад', 'ИИ пишет доклад'. The display label is capitalised and reads as a proper noun
// mid-sentence. Nominative and accusative coincide for all four (inanimate masculine and neuter),
// so one table serves both; an animate type would need its own.
//
// Deliberately NOT derived from WIRE_DOCUMENT_TYPE, which happens to hold the same four strings:
// that map is a boundary translation owned by the backend's vocabulary, this is display copy.
// Coupling them would let a backend rename rewrite what the user reads.
export const DOCUMENT_TYPE_ACCUSATIVE: Record<DocumentType, string> = {
  doklad: 'доклад',
  essay: 'эссе',
  sochinenie: 'сочинение',
  referat: 'реферат',
}

// 'ваш' agrees in gender with what follows — ваш доклад, ваше эссе — so the possessive cannot be a
// constant in the phrase. Private: meaningless outside the one title it builds.
const DOCUMENT_TYPE_POSSESSIVE: Record<DocumentType, string> = {
  doklad: 'ваш',
  essay: 'ваше',
  sochinenie: 'ваше',
  referat: 'ваш',
}

// The composer's field heading, built from the same table the breadcrumb reads — the two sit five
// lines apart on screen, and naming different types would be the visible bug.
export function topicFieldLabel(documentType: DocumentType): string {
  return `Тема ${DOCUMENT_TYPE_GENITIVE[documentType]}`
}

// The generating screen's title (mockup 05). It used to be the literal 'Готовим ваш доклад' in
// DocArea, five lines from a status badge naming the real picked type.
export function generatingTitle(documentType: DocumentType): string {
  return `Готовим ${DOCUMENT_TYPE_POSSESSIVE[documentType]} ${DOCUMENT_TYPE_ACCUSATIVE[documentType]}`
}

// The generating progress line in the chat panel (mockup 05), the same screen's other half.
export function writingProgressMessage(documentType: DocumentType): string {
  return `ИИ пишет ${DOCUMENT_TYPE_ACCUSATIVE[documentType]}`
}

// The three phrases below are not the generating screen, but they share its chat panel within one
// session: the transcript keeps every step on screen, and a run moves pending -> completed/failed
// without a remount. Leaving them hardcoded while the pending line declines would have made one
// panel say `ИИ пишет реферат` and, a state later, `Пишу доклад`.
export function writtenProgressMessage(documentType: DocumentType): string {
  return `Пишу ${DOCUMENT_TYPE_ACCUSATIVE[documentType]}`
}

export function generationFailedTitle(documentType: DocumentType): string {
  return `Не удалось сгенерировать ${DOCUMENT_TYPE_ACCUSATIVE[documentType]}`
}

// The display label for a value that came off the wire. The history list rendered `document_type`
// RAW, so its rows said 'доклад' while the modal that created them said 'Доклад' — the same
// document named two ways, because the list reached for the wire value when the label was one
// lookup away.
//
// An unrecognised type falls back to the server's own string rather than a placeholder: for a type
// this client has never heard of, the wire value is the most informative thing available, and
// 'Неизвестный тип' would be strictly less true.
export function documentTypeLabelFromWire(wire: string): string {
  const appType = documentTypeFromWire(wire)
  return appType ? DOCUMENT_TYPE_LABELS[appType] : wire
}
