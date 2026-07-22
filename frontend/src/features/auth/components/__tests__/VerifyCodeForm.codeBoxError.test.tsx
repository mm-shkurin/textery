import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import { renderWithRouter } from '../../../../test/renderWithRouter'
import { VerifyCodeForm } from '../VerifyCodeForm'
import * as verifyApi from '../../api/verifyApi'

// Scenario 5.5, visual half of the Gherkin: "the code boxes show an error state". The mockup
// (02-verify-code `.code-box.error`) paints every box with a red border on a rejected code. The
// message half is covered by VerifyCodeForm.wrongCode.test.tsx; this pins the box error paint and,
// crucially, that it CLEARS when the user edits — a red border stuck on input the user has already
// changed would accuse a value the server never saw.

vi.mock('../../api/verifyApi', async (importOriginal) => {
  const actual = await importOriginal<typeof verifyApi>()
  return { ...actual, verify: vi.fn() }
})

describe('VerifyCodeForm code-box error state', () => {
  it('paints every code box with the error class after the server rejects the code', async () => {
    vi.mocked(verifyApi.verify).mockRejectedValue({ errorCode: 'INVALID_OR_EXPIRED_CODE', message: '' })
    renderWithRouter(<VerifyCodeForm email="user@example.com" />)

    fireEvent.click(screen.getByTestId('verify-confirm-button'))
    await screen.findByTestId('verify-form-error')

    for (let index = 0; index < 6; index++) {
      expect(screen.getByTestId(`verify-code-input-${index}`)).toHaveClass('error')
    }
  })

  it('paints the boxes on a 200 that reports is_verified:false (not just a rejection)', async () => {
    // The backend has never sent a 200 with is_verified:false, but the form reads the flag rather
    // than trusting the status — an unverified 200 is a wrong-code outcome, so the boxes light up
    // exactly as a rejection does. Distinct code path from the catch branch.
    vi.mocked(verifyApi.verify).mockResolvedValue({ isVerified: false })
    renderWithRouter(<VerifyCodeForm email="user@example.com" />)

    fireEvent.click(screen.getByTestId('verify-confirm-button'))
    await screen.findByTestId('verify-form-error')

    expect(screen.getByTestId('verify-code-input-0')).toHaveClass('error')
  })

  it('clears the error paint as soon as the user edits a box', async () => {
    vi.mocked(verifyApi.verify).mockRejectedValue({ errorCode: 'INVALID_OR_EXPIRED_CODE', message: '' })
    renderWithRouter(<VerifyCodeForm email="user@example.com" />)

    fireEvent.click(screen.getByTestId('verify-confirm-button'))
    await screen.findByTestId('verify-form-error')
    expect(screen.getByTestId('verify-code-input-0')).toHaveClass('error')

    fireEvent.change(screen.getByTestId('verify-code-input-0'), { target: { value: '7' } })

    expect(screen.getByTestId('verify-code-input-0')).not.toHaveClass('error')
  })
})
