import { describe, expect, it } from 'vitest'
import { verifyErrorMessage, WRONG_CODE_MESSAGE } from '../verifyErrorHandling'
import { GENERIC_VERIFY_FAILURE_MESSAGE } from '../authMessages'

// verifyErrorHandling sat at 57% with only its wrong-code arm exercised through the form: the
// relay arm and the fallback — the two that decide what a user sees for every OTHER rejection —
// were unexecuted. Its sibling loginErrorHandling has a test of its own; this closes the gap.
describe('verifyErrorMessage', () => {
  // Both codes mean the same thing to the user, and the backend collapses wrong/expired/
  // no-account/no-code into the first on purpose (the enumeration oracle the story avoids). The
  // copy is FORM-owned, never server-relayed — the api mapper leaves message: '' for these.
  it.each(['INVALID_OR_EXPIRED_CODE', 'INVALID_CODE'])(
    'shows the form-owned wrong-code copy for %s',
    (errorCode) => {
      expect(verifyErrorMessage({ errorCode, message: '' })).toBe(WRONG_CODE_MESSAGE)
    },
  )

  // The relayed-message arm: a coded rejection the form has no copy for still says something
  // specific rather than collapsing to the generic line.
  it('relays a usable server message for any other coded rejection', () => {
    const message = 'Слишком много попыток. Повторите позже.'

    expect(verifyErrorMessage({ errorCode: 'TOO_MANY_ATTEMPTS', message })).toBe(message)
  })

  // A code with nothing readable attached must not render as an empty banner.
  it.each([
    ['an empty message', ''],
    ['a whitespace-only message', '   '],
  ])('falls back to the generic line when a coded rejection carries %s', (_label, message) => {
    expect(verifyErrorMessage({ errorCode: 'SOME_CODE', message })).toBe(
      GENERIC_VERIFY_FAILURE_MESSAGE,
    )
  })

  // Nothing casts the rejection to a declared shape, because at run time nothing holds it to
  // one: a transport failure rejects with a bodyless Error, not with the API's error object.
  it.each([
    ['a transport Error', new Error('Failed to fetch')],
    ['a message without any error code', { message: 'что-то пошло не так' }],
    ['a plain string', 'boom'],
    ['null', null],
    ['undefined', undefined],
  ])('falls back to the generic line for %s', (_label, error) => {
    expect(verifyErrorMessage(error)).toBe(GENERIC_VERIFY_FAILURE_MESSAGE)
  })
})
