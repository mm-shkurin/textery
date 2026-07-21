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
// hazard-scan group 7) only covers strings the backend actually produced. A rejection outside
// that guarantee must never have its text rendered — spec 5.2's non-disclosure clause.
//
// But NOT rendering the server's text is only half the requirement: the form must still say
// SOMETHING. Silence is an illegal terminal state. Spec 5.2's "the message does not indicate
// whether the email exists" is about the ORACLE, not the string — and the mere PRESENCE of the
// error element is an oracle. Once 5.3 lands and the backend answers UNVERIFIED, a wrong
// password on a registered account would render a message while an unverified account renders
// silence: an attacker enumerates by observing whether the div exists, never reading it.
//
// So every non-contract outcome resolves to a client-owned generic constant. 5.3/5.4/5.6 will
// branch distinct messages ABOVE this fallback; INTERNAL_SERVER_ERROR is used here precisely
// because no planned scenario branches on it.
const GENERIC_LOGIN_FAILURE_MESSAGE = 'Не удалось войти'

describe('LoginForm non-contract rejections', () => {
  afterEach(() => {
    vi.mocked(api.login).mockReset()
  })

  // NOTE (5.6 RED, 2026-07-21): the bodyless-transport-failure test that lived here was DELETED,
  // not moved by accident. It pinned `TypeError → login-form-error === GENERIC`, which is exactly
  // the input §5.6 must now turn into a DISTINCT retry-capable network-error state (`login-network-
  // error`, not `login-form-error`). Keeping it would have gone red at 5.6's GREEN, where green-
  // agent (tests-read-only) could not remove it — RED owns this collision (round-3 premortem on
  // 5d40a5a, CREDIBLE). The transport-failure case, including its non-disclosure clause, now lives
  // in LoginForm.networkError.test.tsx (a). The fixtures remaining below all carry an errorCode,
  // so they still route through `login-form-error` and are untouched by the network branch.

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

  // A non-string message satisfies `LoginApiError` at compile time only. This fixture and the
  // array one below guard the `typeof message === 'string'` clause in `isUsableMessage`; the
  // empty/whitespace fixtures cover its `/\S/` clause instead. By this file's own yardstick —
  // the kill set — this fixture is REDUNDANT: it kills {M1}, the array kills {M1, M4}, a strict
  // SUBSET. So it is retained as documentation of a distinct input class rather than as an
  // independent guard (round-6's wording for the empty-string fixture); the opposite mechanisms
  // below are why it documents something, not why it would be a guard.
  //
  // Read THIS fixture's failure honestly: deleting the typeof clause does not leak
  // `internalText` here. React refuses an OBJECT child and throws, so the render dies, the
  // button never re-enables, and the `waitFor` below times out before the text assertions
  // run. Non-disclosure here is enforced by React — a fact about object children ONLY, which
  // does not generalize (see the array fixture, where React is no barrier). What the typeof
  // clause buys here is the property asserted below: a non-string message resolves to the
  // client-owned constant instead of taking the whole login form down.
  //
  // The `not.toContain` below is NOT insurance against a stringifying implementation: the
  // stricter `toBe` above aborts first, so the mutant invoked to justify it never reaches
  // this line. Its only reachable niche is a leak landing elsewhere in `document.body` while
  // the div still shows GENERIC. Kept for that niche alone — true of EVERY `not.toContain`
  // in this file, the array fixture's included; the argument is about assertion ORDER.
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
  // barrier. What catches the leak is the `toBe` below, NOT the `not.toContain`, for the
  // ordering reason given above: under the mutant this test dies AT the `toBe`.
  //
  // React does not treat an array child the way it treats an object child. An ARRAY child is
  // rendered — each element in turn, text verbatim, no throw; that is the mechanism every
  // `.map()` in JSX relies on. So the "React refuses it" reasoning that makes the object
  // fixture safe buys NOTHING here: with the typeof clause gone,
  // `/\S/.test(['NPE at AuthService.line42'])` coerces the array, returns true, and the form
  // renders the internal text into the error div verbatim. The failure is SILENT — a leak on
  // screen, not a crash — the opposite of the object fixture's loud one.
  //
  // MUTATION-VERIFIED (test-review), both mutants grep-confirmed present before running,
  // against this file's 6P/0F baseline:
  //   * `typeof s === 'string' || Array.isArray(s)` — arrays through = 1F/5P in this file;
  //     suite-wide `2 failed | 100 passed (102)`, measured against the `1 failed | 101 passed`
  //     baseline the scenario's own RED already contributes — so exactly ONE new failure, and
  //     it is this fixture. THE LAST BARRIER, not one obstacle: nothing else anywhere
  //     stands between `isUsableMessage` and the leak, so deleting this test leaks silently
  //     with nothing going red. Received 'NPE at AuthService.line42' where GENERIC was
  //     expected — internal text ON SCREEN. The api-layer fixture that would make this a
  //     TWO-layer kill does not fit: `loginApi.test.ts` is AT the 200-line cap.
  //   * dropping the `typeof` clause entirely = 2F/4P, killing this AND the object fixture,
  //     the latter via React's throw rather than a leak.
  //
  // Why this fixture, stated honestly: like the three above it is defence-in-depth on the
  // form's own guard RATHER THAN a claim about what loginApi emits today — nothing at run time
  // holds a rejection to `LoginApiError`, and an array is a distinct way `message` can be
  // present-but-unusable. Its warrant is LOCAL: the mutants above, on this file's own
  // predicate. No backend claim is needed to justify it and none is made here — two earlier
  // revisions tried ("stock Java message-list serialization", then FastAPI's `detail` array)
  // and both were false in the same way: a cross-layer assertion with no test at that layer
  // to hold it. What this file can say is local: `applyLoginError` reads `error.message` and
  // nothing else, so `message` being an array is an input class regardless of who produces it.
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

  // Whitespace-only is truthy, so it clears every guard the empty-string fix installed and is
  // returned verbatim: the div is PRESENT (presence-oracle closed) but renders a blank box —
  // silence by this scenario's own standard, the `''` fix having stopped at truthiness where
  // it needed to stop at "has visible text".
  it('displays the generic message when a contract-shaped rejection carries a whitespace-only message', async () => {
    vi.mocked(api.login).mockRejectedValue({ errorCode: 'INVALID_CREDENTIALS', message: '   ' })
    const { submitButton } = renderAndSubmit()

    await waitFor(() => expect(submitButton).not.toBeDisabled())
    expect(screen.getByTestId('login-form-error').textContent).toBe(GENERIC_LOGIN_FAILURE_MESSAGE)
  })
})
