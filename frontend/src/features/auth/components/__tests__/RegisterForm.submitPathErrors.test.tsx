import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, screen, waitFor } from '@testing-library/react'
import { renderWithRouter } from '../../../../test/renderWithRouter'
import { RegisterForm } from '../RegisterForm'
import * as api from '../../api/registerApi'
import type { RegisterResult } from '../../api/registerApi'
import { GENERIC_REGISTER_FAILURE_MESSAGE } from '../../utils/authMessages'

vi.mock('../../api/registerApi', () => ({
  register: vi.fn(),
}))

// Everything `register` can reject with that ISN'T a duplicate email — the arms
// RegisterForm.duplicateEmail covers one of and leaves the rest of unasserted.
//
// The rule these pin is the one the hook states and the sibling login form already enforces:
// silence is an illegal terminal state. Before that rule landed here, applyRegisterError returned
// null for anything but a duplicate email and the caller's `if (message)` set nothing — a 500, a
// dropped connection, an INVALID_PASSWORD all left the button springing back with no explanation,
// which reads as "the click did nothing" and earns a second identical submit. Against a
// registration endpoint, a second identical submit is a second account attempt.
//
// The generic text is imported from production rather than retyped: what is pinned is that the
// REGISTRATION fallback surfaced, not its current wording. Its login-side twin is a different
// constant on purpose (stamping one onto the other's failure forges provenance), and importing it
// is what would let this test still pass if they were confused.

const VALID_EMAIL = 'user@example.com'
const VALID_PASSWORD = 'Str0ng!Pass'

const REGISTER_SUCCESS: RegisterResult = {
  userId: '00000000-0000-0000-0000-000000000001',
  email: VALID_EMAIL,
  isVerified: false,
  verificationCode: '123456',
  codeExpiresAt: '2026-07-16T18:00:00+00:00',
}

function renderAndFill() {
  renderWithRouter(<RegisterForm />)
  fireEvent.change(screen.getByTestId('register-email-input'), {
    target: { value: VALID_EMAIL },
  })
  fireEvent.change(screen.getByTestId('register-password-input'), {
    target: { value: VALID_PASSWORD },
  })
  fireEvent.change(screen.getByTestId('register-confirm-password-input'), {
    target: { value: VALID_PASSWORD },
  })
  return screen.getByTestId('register-submit-button')
}

async function expectGenericFailure() {
  const error = await screen.findByTestId('register-email-error')
  expect(error).toHaveTextContent(GENERIC_REGISTER_FAILURE_MESSAGE)
}

describe('RegisterForm submit failures that are not a duplicate email', () => {
  afterEach(() => {
    vi.mocked(api.register).mockReset()
  })

  it('explains a transport failure rather than leaving the form silent', async () => {
    // A dropped connection: an Error, no errorCode at all. This is the shape that reached the
    // `'errorCode' in error` guard as `false` and fell through to a `null` message.
    vi.mocked(api.register).mockRejectedValue(new Error('Failed to fetch'))

    fireEvent.click(renderAndFill())

    await expectGenericFailure()
  })

  it('explains a server error code the form has no dedicated copy for', async () => {
    vi.mocked(api.register).mockRejectedValue({
      errorCode: 'INVALID_PASSWORD',
      message: 'Password does not meet the policy.',
    })

    fireEvent.click(renderAndFill())

    // The server's text is NOT rendered here, and that is deliberate rather than an oversight:
    // the duplicate-email code is the one whose message this form quotes. Any other code carries
    // text written for an API consumer - frequently English, occasionally a stack-shaped
    // sentence - and the client-owned constant is the only string known to be addressed to a user.
    await expectGenericFailure()
    expect(screen.queryByText('Password does not meet the policy.')).not.toBeInTheDocument()
  })

  it('falls back to the generic message when the duplicate-email body carries blank text', async () => {
    // The duplicate CODE with an unusable message. `'   '` rather than `''` because it is truthy:
    // a guard written as `if (message)` accepts it and renders an empty error box, which is the
    // silence this whole suite is about, dressed as a rendered element.
    vi.mocked(api.register).mockRejectedValue({
      errorCode: 'EMAIL_ALREADY_REGISTERED',
      message: '   ',
    })

    fireEvent.click(renderAndFill())

    await expectGenericFailure()
  })

  it('ignores a second submit while the first is still in flight', async () => {
    let resolveRegister: (value: RegisterResult) => void = () => {}
    vi.mocked(api.register).mockReturnValue(
      new Promise((resolve) => {
        resolveRegister = resolve
      }),
    )
    const submitButton = renderAndFill()

    // Both clicks are dispatched at the form, not gated on the button's disabled state: a
    // disabled attribute is a render-time courtesy, and Enter in a text field, a double click
    // landing inside the same frame, or an assistive tool submitting the form all bypass it. The
    // hook's own re-entrancy guard is what has to hold, and this is the only way to observe it.
    fireEvent.click(submitButton)
    fireEvent.click(submitButton)
    fireEvent.submit(submitButton.closest('form') as HTMLFormElement)

    await waitFor(() => expect(api.register).toHaveBeenCalledTimes(1))
    resolveRegister(REGISTER_SUCCESS)
  })
})
