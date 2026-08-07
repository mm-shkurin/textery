import { describe, expect, it } from 'vitest'
import { accountEmailFromToken, accountInitials } from '../accountEmail'

// The real token shape: `jwt_token_service._encode` signs {sub, email, type, iat, exp}. Built here
// rather than pasted as a literal so the claim under test is visible in the test that asserts it.
function tokenWithPayload(payload: Record<string, unknown>): string {
  const encode = (value: object) =>
    btoa(String.fromCharCode(...new TextEncoder().encode(JSON.stringify(value))))
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=+$/, '')

  return `${encode({ alg: 'HS256', typ: 'JWT' })}.${encode(payload)}.signature-not-verified`
}

describe('accountEmailFromToken', () => {
  it('reads the email claim the backend puts in every access token', () => {
    const token = tokenWithPayload({
      sub: '0f2a1e1c-1b2c-4d5e-8f90-abcdefabcdef',
      email: 'emailname@gmail.com',
      type: 'access',
    })

    expect(accountEmailFromToken(token)).toBe('emailname@gmail.com')
  })

  // The claim is UTF-8 on the wire, and `atob` yields bytes: reading those bytes as a string
  // directly turns a Cyrillic address into mojibake on the user's own account menu.
  it('decodes a non-ASCII address without mangling it', () => {
    const token = tokenWithPayload({ email: 'почта@яндекс.рф', type: 'access' })

    expect(accountEmailFromToken(token)).toBe('почта@яндекс.рф')
  })

  // Every one of these is reachable — no session, a test double holding a plain string, a token
  // truncated in storage, an OAuth path that one day omits the claim. None may render as text.
  it.each([
    ['no token at all', null],
    ['a string that is not a JWT', 'test-access-token'],
    ['a token whose payload is not base64', 'header.!!!not-base64!!!.signature'],
    ['a token with no email claim', tokenWithPayload({ sub: 'abc', type: 'access' })],
    ['a token whose email claim is blank', tokenWithPayload({ email: '   ', type: 'access' })],
    ['a token whose email claim is not a string', tokenWithPayload({ email: 42 })],
  ])('returns null for %s', (_case, token) => {
    expect(accountEmailFromToken(token)).toBeNull()
  })
})

describe('accountInitials', () => {
  // Two letters only when the address itself carries two words. A second letter invented from a
  // single word would be indistinguishable from a real initial.
  it.each([
    ['emailname@gmail.com', 'E'],
    ['ivan.petrov@mail.ru', 'IP'],
    ['anna_ivanova@yandex.ru', 'AI'],
    ['a-b-c@example.com', 'AB'],
    ['почта@яндекс.рф', 'П'],
  ])('derives %s -> %s', (email, expected) => {
    expect(accountInitials(email)).toBe(expected)
  })
})
