/**
 * The register a generated text is written in — the wire vocabulary plus what a person reads.
 *
 * In `shared/` rather than inside `features/generation`, and the module boundary check is what
 * forced the question: TWO features name these values. Generation collects the register on the
 * composer form; projects re-chooses it on «перегенерировать в другом стиле». A vocabulary two
 * features must agree on is not either feature's private business — a copy in each is how the
 * projects card ends up offering a fourth register the server refuses.
 */

// Cyrillic because that IS the contract: `domain/src/generation/text_style.py` validates against
// these exact strings, the same way `document_type` is Cyrillic on the wire.
export const TEXT_STYLES = ['научный', 'публицистический', 'художественный'] as const

export type TextStyle = (typeof TEXT_STYLES)[number]

// What the picker shows for each register, and the one-line explanation under it. A user choosing
// between «публицистический» and «художественный» from the labels alone is guessing; the
// descriptions are what make the choice mean something.
export const TEXT_STYLE_OPTIONS: ReadonlyArray<{
  value: TextStyle
  label: string
  hint: string
}> = [
  { value: 'научный', label: 'Научный', hint: 'Термины, безличные конструкции' },
  { value: 'публицистический', label: 'Публицистический', hint: 'Живая аргументация, примеры' },
  { value: 'художественный', label: 'Художественный', hint: 'Образная речь, описания' },
]
