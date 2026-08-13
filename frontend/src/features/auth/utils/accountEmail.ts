// The avatar's letters, and nothing else.
//
// HISTORY: this module used to DECODE the access token to find the account's address
// (`accountEmailFromToken` / `currentAccountEmail`), because there was no `GET /me` to ask. Story
// 13 built that endpoint, so the address now comes from the server over `features/profile`, and
// both decoders were deleted rather than left as a second, quietly diverging source of identity.
// Do not reintroduce them: a token payload is not a profile — it carries no `name`, and it goes
// stale against a rename the moment the user saves one.

// Splitting a string with `[...s]` yields CODE POINTS, and `s[0]` yields a UTF-16 UNIT. On an
// astral first character (an emoji, a rare CJK ideograph) the unit is a lone surrogate, which
// renders as U+FFFD — a black diamond where an initial should be. That never surfaced while the
// only input was the local part of an email address, which is ASCII-ish in practice; a display
// name is free user text and hits it immediately.
//
// A code point is still not the last word — a grapheme is (a base letter plus a combining accent,
// a flag, an emoji with a skin-tone modifier are each ONE thing the reader sees). `Intl.Segmenter`
// gives that where it exists; the code-point split is the fallback, never `[0]`.
function firstGrapheme(word: string): string {
  const segmenter = typeof Intl.Segmenter === 'function' ? new Intl.Segmenter() : null
  if (segmenter === null) {
    return [...word][0] ?? ''
  }
  const first = segmenter.segment(word)[Symbol.iterator]().next()
  return first.done === true ? '' : first.value.segment
}

function initialsFrom(words: string[]): string {
  return words.slice(0, 2).map(firstGrapheme).join('').toLocaleUpperCase('ru-RU')
}

// A name's words are separated by whitespace: "Анна Ковалёва" → "АК". The address is the
// fallback, and its only evidence of a second word is a separator in the local part:
// "ivan.petrov@mail.ru" → "IP", "emailname@gmail.com" → "E". Inventing a second letter from a
// single word would be inventing data — one letter is the honest answer.
export function accountInitials(identity: { name: string | null; email: string }): string {
  const name = identity.name?.trim() ?? ''
  if (name !== '') {
    return initialsFrom(name.split(/\s+/).filter((word) => word !== ''))
  }
  return initialsFrom(
    identity.email
      .split('@')[0]
      .split(/[._\-+]+/)
      .filter((word) => word !== ''),
  )
}
