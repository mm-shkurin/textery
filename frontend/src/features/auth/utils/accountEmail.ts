import { getAccessToken } from './authSession'

// The signed-in user's own email, read from the access token the backend already issued.
//
// There is no `GET /me` on the backend (verified against the OpenAPI document: register / verify
// / login / refresh / oauth, and nothing else), so a request for the address would have nowhere
// to go. The access token carries it: `jwt_token_service._encode` puts `email` next to `sub` in
// every access and refresh token, and the client is already holding that token to send it.
//
// This DECODES, it does not verify. The payload is read for one purpose — printing the address
// back to the person who typed it — and a forged token buys an attacker nothing here but a
// wrong label on their own screen. Nothing downstream trusts this value: authorization is the
// backend's 401. Never widen this into an authorization check.
const PAYLOAD_SEGMENT = 1

function decodeSegment(segment: string): string | null {
  try {
    const base64 = segment.replace(/-/g, '+').replace(/_/g, '/')
    // `atob` rejects an unpadded length in strict implementations, and JWT segments are stripped
    // of their '=' by construction — so the padding is put back rather than hoped for.
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=')
    const binary = window.atob(padded)
    // The claim is UTF-8 on the wire and an email may be non-ASCII; `atob` yields bytes, so
    // decoding through TextDecoder rather than using the string directly keeps those intact.
    return new TextDecoder().decode(Uint8Array.from(binary, (char) => char.charCodeAt(0)))
  } catch {
    return null
  }
}

// Anything that is not a token carrying a non-blank string `email` is `null` — a missing claim, a
// non-JWT string (tests hold one), a truncated token. The callers render an account without a
// visible address rather than the word "undefined".
export function accountEmailFromToken(token: string | null): string | null {
  const segment = token?.split('.')[PAYLOAD_SEGMENT]
  if (!segment) return null

  const json = decodeSegment(segment)
  if (json === null) return null

  try {
    const claims: unknown = JSON.parse(json)
    if (typeof claims !== 'object' || claims === null) return null
    const email = (claims as Record<string, unknown>).email
    return typeof email === 'string' && /\S/.test(email) ? email : null
  } catch {
    return null
  }
}

export function currentAccountEmail(): string | null {
  return accountEmailFromToken(getAccessToken())
}

// The avatar's letters. The design draws two ("АИ") because it was drawn against a full name,
// and the account has no name — only the address. So the initials are derived from the address
// itself: "ivan.petrov@mail.ru" → "IP", "emailname@gmail.com" → "E". Separators are the only
// evidence of a second word an email carries; inventing a second letter from a single word would
// be inventing data.
export function accountInitials(email: string): string {
  const words = email
    .split('@')[0]
    .split(/[._\-+]+/)
    .filter((word) => word !== '')
  const letters = words.slice(0, 2).map((word) => word[0])
  return letters.join('').toUpperCase()
}
