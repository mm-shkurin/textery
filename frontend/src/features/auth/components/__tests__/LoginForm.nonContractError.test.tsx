import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, screen, waitFor } from '@testing-library/react'
import { renderWithRouter } from '../../../../test/renderWithRouter'
import { LoginForm } from '../LoginForm'
import * as api from '../../api/loginApi'

vi.mock('../../api/loginApi', () => ({
  login: vi.fn(),
}))

const EMAIL = 'user@example.com'
const PASSWORD = 'Str0ng!Pass'

function renderAndSubmit() {
  renderWithRouter(<LoginForm />)
  fireEvent.change(screen.getByTestId('login-email-input'), { target: { value: EMAIL } })
  fireEvent.change(screen.getByTestId('login-password-input'), { target: { value: PASSWORD } })
  const submitButton = screen.getByTestId('login-submit-button')
  fireEvent.click(submitButton)
  return { submitButton }
}

// The backend's "message is always generic and client-safe" guarantee (endpoints.md,
// hazard-scan group 7) only covers strings the backend actually produced. A rejection
// outside that guarantee must never have its text rendered — spec 5.2's non-disclosure
// clause.
//
// But NOT rendering the server's text is only half the requirement: the form must still
// say SOMETHING. Silence is an illegal terminal state. Spec 5.2's "the message does not
// indicate whether the email exists" is about the ORACLE, not the string — and the mere
// PRESENCE of the error element is an oracle. Once 5.3 lands and the backend answers
// UNVERIFIED for a registered-but-unverified account, a wrong password on a registered
// account would render a message while an unverified account renders silence: an attacker
// enumerates accounts by observing whether the div exists, never needing to read it.
//
// So every non-contract outcome resolves to a client-owned generic constant. 5.3/5.4/5.6
// will branch their own distinct messages ABOVE this fallback; INTERNAL_SERVER_ERROR is
// used here precisely because no planned scenario branches on it.
const GENERIC_LOGIN_FAILURE_MESSAGE = 'Не удалось войти'

describe('LoginForm non-contract rejections', () => {
  afterEach(() => {
    vi.mocked(api.login).mockReset()
  })

  // A transport failure is not an enumeration oracle — it cannot be induced per-account —
  // but it is the MOST common trigger of the silent form, so the fallback must cover it too.
  // 5.6 owns the retry-capable network state and will branch it ABOVE this fallback; until
  // then the fallback is what stands between a failed fetch and a blank form. Pinning
  // silence here would instead force green to write a TypeError-discriminating branch whose
  // only purpose is to preserve the incident this scenario exists to kill.
  it('displays the generic message, not the transport failure text, when login rejects with a bodyless transport failure', async () => {
    const transportText = 'Failed to fetch'
    vi.mocked(api.login).mockRejectedValue(new TypeError(transportText))
    const { submitButton } = renderAndSubmit()

    await waitFor(() => expect(submitButton).not.toBeDisabled())
    expect(screen.getByTestId('login-form-error').textContent).toBe(GENERIC_LOGIN_FAILURE_MESSAGE)
    expect(document.body.textContent).not.toContain(transportText)
  })

  it('displays the generic message, not the server text, when login rejects with an unrecognised error code', async () => {
    const serverText = 'NullPointerException at AuthService.line42'
    vi.mocked(api.login).mockRejectedValue({
      errorCode: 'INTERNAL_SERVER_ERROR',
      message: serverText,
    })
    const { submitButton } = renderAndSubmit()

    await waitFor(() => expect(submitButton).not.toBeDisabled())
    expect(screen.getByTestId('login-form-error').textContent).toBe(GENERIC_LOGIN_FAILURE_MESSAGE)
    expect(document.body.textContent).not.toContain(serverText)
  })

  // `LoginApiError` is an unenforced compile-time type and the form's catch takes
  // `unknown`, so nothing at runtime holds loginApi to the declared shape. These three
  // fixtures are defence-in-depth on the form's own guard rather than a claim about what
  // loginApi emits today: each one names a distinct way a `message` can be present-but-
  // unusable, and each must resolve to the client-owned constant rather than to silence
  // or to raw server text.
  it('displays the generic message when a contract-shaped rejection carries an empty message', async () => {
    vi.mocked(api.login).mockRejectedValue({ errorCode: 'INVALID_CREDENTIALS', message: '' })
    const { submitButton } = renderAndSubmit()

    await waitFor(() => expect(submitButton).not.toBeDisabled())
    expect(screen.getByTestId('login-form-error').textContent).toBe(GENERIC_LOGIN_FAILURE_MESSAGE)
  })

  // A non-string message satisfies `LoginApiError` at compile time only. This fixture and
  // the array one below guard the `typeof message === 'string'` clause in `isUsableMessage`;
  // the empty/whitespace fixtures cover its `/\S/` clause instead. The two non-string
  // fixtures are NOT redundant — they fail by opposite mechanisms, and only one of them is
  // a disclosure risk.
  //
  // Read THIS fixture's failure honestly: deleting the typeof clause does not leak
  // `internalText` here. `{formError}` as a JSX child is not string-coerced — React refuses
  // an OBJECT child and throws, so the render dies, the button never re-enables, and the
  // `waitFor` below times out before the text assertions are reached. There is no
  // `[object Object]` on screen. Non-disclosure for THIS fixture is enforced by React, and
  // that is a fact about object children ONLY — it does not generalize to non-strings (see
  // the array fixture, where React is no barrier at all). What the typeof clause buys here
  // is the property asserted below: a non-string message resolves to the client-owned
  // constant instead of taking the whole login form down.
  //
  // The `not.toContain` below is NOT insurance against a stringifying implementation, as it
  // was once justified: the stricter `toBe` on the line above aborts the test first, so the
  // very mutant invoked to justify it can never reach this line. Its only reachable niche is
  // a leak landing elsewhere in `document.body` while the div still shows GENERIC. Kept for
  // that niche alone — and that holds for EVERY `not.toContain` in this file, the array
  // fixture's included. The argument is about assertion ORDER, not about which fixture it
  // is, so no fixture here gets to claim its `not.toContain` is the one doing the catching.
  it('displays the generic message when a contract-shaped rejection carries an object message', async () => {
    const internalText = 'NPE at AuthService.line42'
    vi.mocked(api.login).mockRejectedValue({
      errorCode: 'INVALID_CREDENTIALS',
      message: { internal: internalText },
    })
    const { submitButton } = renderAndSubmit()

    await waitFor(() => expect(submitButton).not.toBeDisabled())
    expect(screen.getByTestId('login-form-error').textContent).toBe(GENERIC_LOGIN_FAILURE_MESSAGE)
    expect(document.body.textContent).not.toContain(internalText)
  })

  // THE ARRAY MESSAGE — the one non-string fixture where the `typeof` clause is the ONLY
  // barrier. What catches the leak is the `toBe` below, NOT the `not.toContain`, for exactly
  // the ordering reason given above: under the mutant this test dies AT the `toBe`, and the
  // `not.toContain` line never executes.
  //
  // MUTATION-VERIFIED (test-review), both mutants grep-confirmed present before running,
  // against this file's 6P/0F baseline:
  //   * `typeof s === 'string' || Array.isArray(s)` — let arrays through = 1F/5P, killing
  //     THIS TEST ALONE. Received: 'NPE at AuthService.line42' where the GENERIC constant was
  //     expected — the internal text rendered ON SCREEN. Its reason to exist.
  //   * dropping the `typeof` clause entirely = 2F/4P, killing this AND the object fixture,
  //     the latter via React's throw rather than a leak.
  //
  // React does not treat an array child the way it treats an object child. An ARRAY child is
  // rendered — each element in turn, text verbatim, no throw. That is not an edge case, it is
  // the mechanism every `.map()` in JSX relies on. So the "React refuses it" reasoning that
  // makes the object fixture safe buys NOTHING here: with the typeof clause gone,
  // `/\S/.test(['NPE at AuthService.line42'])` coerces the array to its string form, returns
  // true, and the form renders the internal text into the error div verbatim. The failure is
  // SILENT — a leak on screen, not a crash — which is the opposite of the object fixture's
  // loud one.
  //
  // Nor is the fixture exotic. `message: ["Invalid credentials", "NPE at AuthService.line42"]`
  // is stock Java message-list validation-error serialization; a backend that adds field-level
  // errors emits exactly this shape without anyone deciding to change the contract.
  it('displays the generic message, not the array text, when a contract-shaped rejection carries an array message', async () => {
    const internalText = 'NPE at AuthService.line42'
    vi.mocked(api.login).mockRejectedValue({
      errorCode: 'INVALID_CREDENTIALS',
      message: [internalText],
    })
    const { submitButton } = renderAndSubmit()

    await waitFor(() => expect(submitButton).not.toBeDisabled())
    expect(screen.getByTestId('login-form-error').textContent).toBe(GENERIC_LOGIN_FAILURE_MESSAGE)
    expect(document.body.textContent).not.toContain(internalText)
  })

  // Whitespace-only is truthy, so it clears every guard the empty-string fix installed and
  // is returned verbatim: the div is PRESENT (the presence-oracle stays closed) but renders
  // a blank box. Silence by this scenario's own standard — the `''` fix stopped at
  // truthiness where it needed to stop at "has visible text".
  it('displays the generic message when a contract-shaped rejection carries a whitespace-only message', async () => {
    vi.mocked(api.login).mockRejectedValue({ errorCode: 'INVALID_CREDENTIALS', message: '   ' })
    const { submitButton } = renderAndSubmit()

    await waitFor(() => expect(submitButton).not.toBeDisabled())
    expect(screen.getByTestId('login-form-error').textContent).toBe(GENERIC_LOGIN_FAILURE_MESSAGE)
  })
})
