import { describe, expect, it } from 'vitest'
import { accountInitials } from '../accountEmail'

// The token-decoding tests that used to live here went with the functions they covered:
// `accountEmailFromToken` / `currentAccountEmail` were deleted when story 13 moved identity onto
// `GET /api/v1/auth/me`. What is left is the avatar's letters, which are still derived on the
// client.

describe('accountInitials', () => {
  // Two letters only when the source itself carries two words. A second letter invented from a
  // single word would be indistinguishable from a real initial.
  it.each([
    ['emailname@gmail.com', 'E'],
    ['ivan.petrov@mail.ru', 'IP'],
    ['anna_ivanova@yandex.ru', 'AI'],
    ['a-b-c@example.com', 'AB'],
    ['почта@яндекс.рф', 'П'],
  ])('falls back to the address: %s -> %s', (email, expected) => {
    expect(accountInitials({ name: null, email })).toBe(expected)
  })

  it('prefers the display name once there is one', () => {
    expect(accountInitials({ name: 'Анна Ковалёва', email: 'anna.ivanova@example.com' })).toBe('АК')
  })

  // `word[0]` is a UTF-16 unit. On an astral first character it is a lone surrogate, which renders
  // as U+FFFD — a black diamond in the corner of every authenticated page. It was safe on the
  // local part of an address only by accident; a display name is free user text.
  it('takes a whole grapheme, not a UTF-16 unit', () => {
    expect(accountInitials({ name: '🎓 Студент', email: 'x@example.com' })).toBe('🎓С')
  })
})
