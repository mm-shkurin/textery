export type DocumentType = 'doklad' | 'essay' | 'sochinenie' | 'referat'

export interface DocumentTypeOption {
  id: DocumentType
  name: string
  available: boolean
  // The line under the name on the creation modal's card — what the type IS, in the words the
  // Figma frame «Мои проекты - Создать проект» (788:5094) uses. It sits beside `name` rather than
  // in the component because it is copy, and the component that renders it is not the only screen
  // that will want to say what a доклад is.
  description: string
}

// All four are selectable. `available` stays on the option rather than being deleted: it is the
// modal's «скоро» affordance, and the next type to be specced before it can be generated needs it
// again. Three of these were false because the backend could not produce them — it can now:
// `SUPPORTED_DOCUMENT_TYPES` has admitted all four since story 1, and since scenario 2.1 every one
// of them reaches the model through the domain's own `build_prompt`, which carries реферат's
// section template and the invented-sources ban.
//
// Ordered as the creation modal draws them — Реферат, Эссе, Доклад, Сочинение. The order is a
// design decision and this is the list every screen renders, so it is stated here rather than
// sorted at each call site.
export const DOCUMENT_TYPES: DocumentTypeOption[] = [
  { id: 'referat', name: 'Реферат', available: true, description: 'Изложение темы с выводами' },
  { id: 'essay', name: 'Эссе', available: true, description: 'Личный взгляд на проблему' },
  { id: 'doklad', name: 'Доклад', available: true, description: 'Текст для устного выступления' },
  {
    id: 'sochinenie',
    name: 'Сочинение',
    available: true,
    description: 'Рассуждение на тему с позицией',
  },
]

export const DEFAULT_DOCUMENT_TYPE: DocumentType = 'doklad'

// Display labels, derived from DOCUMENT_TYPES rather than written out again. App.tsx used to
// carry its own copy of these four strings — a second hand-maintained table of the same facts,
// which is the arrangement this file already warns against for the wire values below. Renaming
// a card in the modal now renames it in the editor's breadcrumb, because there is one source.
export const DOCUMENT_TYPE_LABELS = Object.fromEntries(
  DOCUMENT_TYPES.map((t) => [t.id, t.name]),
) as Record<DocumentType, string>

// Genitive forms, for copy that names the type inside a phrase — 'Тема доклада', not 'Тема
// Доклад'. Russian declines, so a label cannot be concatenated into a sentence and stay
// grammatical; the composer's field heading was a hardcoded 'Тема доклада' precisely because
// interpolating `name` produces nonsense for every other type.
//
// Hand-written and exhaustive for the same reason as WIRE_DOCUMENT_TYPE below: this cannot be
// derived from `name` by any rule (доклад -> доклада, эссе -> эссе, сочинение -> сочинения),
// and adding a member to DocumentType without a form here is a compile error in the file that
// has to know.
export const DOCUMENT_TYPE_GENITIVE: Record<DocumentType, string> = {
  doklad: 'доклада',
  essay: 'эссе',
  sochinenie: 'сочинения',
  referat: 'реферата',
}

// The composer's field heading. Lives here rather than in the component so the phrase is built
// from the same table the breadcrumb reads — the two sit five lines apart on screen, and naming
// different types would be the visible bug.
export function topicFieldLabel(documentType: DocumentType): string {
  return `Тема ${DOCUMENT_TYPE_GENITIVE[documentType]}`
}

// Lowercase nominative/accusative form, for copy that names the type as the object of a verb —
// 'Готовим ваш доклад', 'ИИ пишет доклад'. Same reason as the genitive table above: the display
// label is capitalised ('Доклад') and interpolating it mid-sentence reads as a proper noun.
// Nominative and accusative coincide for all four (inanimate masculine and neuter), so one table
// serves both positions; add an animate type and it will need its own.
//
// Deliberately NOT derived from WIRE_DOCUMENT_TYPE, which happens to hold the same four strings:
// that map is a boundary translation owned by the backend's vocabulary, and this one is display
// copy. Coupling them would mean a backend rename silently rewrites what the user reads.
export const DOCUMENT_TYPE_ACCUSATIVE: Record<DocumentType, string> = {
  doklad: 'доклад',
  essay: 'эссе',
  sochinenie: 'сочинение',
  referat: 'реферат',
}

// 'ваш' agrees in gender with what follows — ваш доклад, ваше эссе — so the possessive cannot be
// a constant in the phrase. Kept private: it is meaningless outside the one title it builds.
const DOCUMENT_TYPE_POSSESSIVE: Record<DocumentType, string> = {
  doklad: 'ваш',
  essay: 'ваше',
  sochinenie: 'ваше',
  referat: 'ваш',
}

// The generating screen's title (mockup 05). Built here, next to the tables it declines against,
// for the reason topicFieldLabel exists: it used to be the literal 'Готовим ваш доклад' in
// DocArea, five lines from a status badge naming the real picked type.
export function generatingTitle(documentType: DocumentType): string {
  return `Готовим ${DOCUMENT_TYPE_POSSESSIVE[documentType]} ${DOCUMENT_TYPE_ACCUSATIVE[documentType]}`
}

// The generating progress line in the chat panel (mockup 05), the same screen's other half.
export function writingProgressMessage(documentType: DocumentType): string {
  return `ИИ пишет ${DOCUMENT_TYPE_ACCUSATIVE[documentType]}`
}

// The three phrases below are NOT the generating screen, but they share its chat panel and its doc
// area within one session: the progress transcript keeps every step on screen, and a run moves
// pending -> completed/failed without a remount. Leaving them hardcoded while the pending line
// declines would have made one panel say `ИИ пишет реферат` and, a state later, `Пишу доклад` —
// two document types named to the same user about the same run, which is worse than being
// consistently wrong. They decline against tables that already exist, so nothing is owed for them.
export function writtenProgressMessage(documentType: DocumentType): string {
  return `Пишу ${DOCUMENT_TYPE_ACCUSATIVE[documentType]}`
}

export function generationFailedTitle(documentType: DocumentType): string {
  return `Не удалось сгенерировать ${DOCUMENT_TYPE_ACCUSATIVE[documentType]}`
}

// The idle doc area's prompt, genitive like the composer heading it sits beside.
export function topicPromptTitle(documentType: DocumentType): string {
  return `Опишите тему ${DOCUMENT_TYPE_GENITIVE[documentType]}`
}

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

// The display label for a value that came off the wire. The history list rendered
// `document_type` RAW, so its rows said 'доклад' while the modal that created them and the
// editor's breadcrumb both said 'Доклад' — the same document, named two ways, because the list
// reached for the wire value when the label was one lookup away.
//
// An unrecognised type falls back to the server's own string rather than to a placeholder: for a
// type this client has never heard of, the wire value is the most informative thing available,
// and 'Неизвестный тип' would be strictly less true. Same reasoning as documentTypeFromWire's
// null — the row stays useful, it just cannot be opened.
export function documentTypeLabelFromWire(wire: string): string {
  const appType = documentTypeFromWire(wire)
  return appType ? DOCUMENT_TYPE_LABELS[appType] : wire
}
