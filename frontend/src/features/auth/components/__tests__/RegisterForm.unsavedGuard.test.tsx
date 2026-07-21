import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, screen, waitFor } from '@testing-library/react'
import { renderWithRouter } from '../../../../test/renderWithRouter'
import { RegisterForm } from '../RegisterForm'
import * as api from '../../api/registerApi'
import type { RegisterResult } from '../../api/registerApi'

// Scenario 5.8 — Un-submitted registration input is confirmed or restored on navigation
// away. tests/02_UI_Tests.md §5.8 permits EITHER a confirm-before-leaving guard OR restoring
// the typed values; "data is not silently discarded" is the invariant. We pin the confirm-guard
// variant: RegisterForm holds email/password/confirm in refs, so the restore variant would mean
// persisting a plaintext password to storage, which the story's credential-handling notes forbid.
// The guard arms a `beforeunload` handler that cancels the event ONLY while the form holds
// UNSAVED input, and stays silent when the form is pristine or has been SUCCESSFULLY submitted
// (the data was sent — no longer unsaved). A submit that FAILS keeps the guard: that data is
// still unsaved and still worth protecting.

vi.mock('../../api/registerApi', () => ({ register: vi.fn() }))

const VALID_EMAIL = 'user@example.com'
const VALID_PASSWORD = 'Str0ng!Pass'
const REGISTER_SUCCESS: RegisterResult = {
  userId: '00000000-0000-0000-0000-000000000001',
  email: VALID_EMAIL,
  isVerified: false,
  verificationCode: '123456',
  codeExpiresAt: '2026-07-16T18:00:00+00:00',
}

function dispatchBeforeUnload() {
  const event = new Event('beforeunload', { cancelable: true })
  window.dispatchEvent(event)
  return event
}

function fillAllFields() {
  fireEvent.change(screen.getByTestId('register-email-input'), { target: { value: VALID_EMAIL } })
  fireEvent.change(screen.getByTestId('register-password-input'), { target: { value: VALID_PASSWORD } })
  fireEvent.change(screen.getByTestId('register-confirm-password-input'), { target: { value: VALID_PASSWORD } })
}

afterEach(() => vi.mocked(api.register).mockReset())

describe.skip('RegisterForm unsaved-input navigation guard', () => {
  it('arms a beforeunload confirm guard once a field has been typed into', () => {
    renderWithRouter(<RegisterForm />)

    fireEvent.change(screen.getByTestId('register-email-input'), {
      target: { value: 'partial@example.ru' },
    })
    const event = dispatchBeforeUnload()

    expect(event.defaultPrevented).toBe(true)
  })

  it('does not arm the guard while the form is pristine and untouched', () => {
    renderWithRouter(<RegisterForm />)

    const event = dispatchBeforeUnload()

    expect(event.defaultPrevented).toBe(false)
  })

  it('drops the guard once the form has been SUCCESSFULLY submitted', async () => {
    vi.mocked(api.register).mockResolvedValue(REGISTER_SUCCESS)
    renderWithRouter(<RegisterForm />)

    fillAllFields()
    fireEvent.click(screen.getByTestId('register-submit-button'))
    // The input was sent — it is no longer unsaved, so the guard must release.
    await waitFor(() => expect(api.register).toHaveBeenCalledTimes(1))
    const event = dispatchBeforeUnload()

    expect(event.defaultPrevented).toBe(false)
  })

  it('KEEPS the guard when a submit FAILS — the data is still unsaved', async () => {
    vi.mocked(api.register).mockRejectedValue(new Error('network down'))
    renderWithRouter(<RegisterForm />)

    fillAllFields()
    fireEvent.click(screen.getByTestId('register-submit-button'))
    await waitFor(() => expect(api.register).toHaveBeenCalledTimes(1))
    const event = dispatchBeforeUnload()

    expect(event.defaultPrevented).toBe(true)
  })
})
