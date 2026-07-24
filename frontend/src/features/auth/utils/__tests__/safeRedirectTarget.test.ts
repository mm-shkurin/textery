import { describe, expect, it } from 'vitest'
import { safeRedirectTarget } from '../safeRedirectTarget'

// The post-sign-in destination comes from router state, which is reachable from a crafted link —
// so this function is the open-redirect guard, and it is worth testing at the unit level rather
// than only through LoginForm: the component test proves one honoured path, and an open redirect
// is proved by what is REFUSED.
describe('safeRedirectTarget', () => {
  it.each([
    ['a plain in-app path', '/history'],
    ['a nested path', '/documents/doc-1/edit'],
    ['the root itself', '/'],
    ['a path carrying a query string', '/history?tab=generations'],
    ['a path carrying a fragment', '/history#latest'],
  ])('honours %s', (_label, from) => {
    expect(safeRedirectTarget(from)).toBe(from)
  })

  // Every one of these is the same attack in a different costume: a URL the browser resolves
  // against another origin. The backslash forms matter because browsers normalise `\` to `/` in
  // the authority position, so a guard written as `!from.startsWith('//')` passes them.
  it.each([
    ['a protocol-relative URL', '//evil.com'],
    ['a backslash protocol-relative URL', '/\\evil.com'],
    ['a mixed slash-backslash URL', '/\\/evil.com'],
    ['a backslash after a double slash', '//\\evil.com'],
    ['an absolute http URL', 'http://evil.com'],
    ['an absolute https URL', 'https://evil.com'],
    ['a javascript: URL', 'javascript:alert(1)'],
    ['a data: URL', 'data:text/html,<script>alert(1)</script>'],
    ['a relative path with no leading slash', 'evil.com'],
    ['a backslash anywhere in the path', '/history\\..\\evil.com'],
    ['an empty string', ''],
  ])('refuses %s and falls back to the root', (_label, from) => {
    expect(safeRedirectTarget(from)).toBe('/')
  })

  // `from` is typed `unknown` because router state is: nothing guarantees a caller put a string
  // there, and a non-string must not reach `navigate()`.
  it.each([
    ['null', null],
    ['undefined', undefined],
    ['a number', 42],
    ['an object', { pathname: '/history' }],
    ['an array', ['/history']],
  ])('falls back to the root for %s', (_label, from) => {
    expect(safeRedirectTarget(from)).toBe('/')
  })
})
