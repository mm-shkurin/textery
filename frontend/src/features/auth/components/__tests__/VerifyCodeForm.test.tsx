import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import { renderWithRouter } from '../../../../test/renderWithRouter'
import { VerifyCodeForm } from '../VerifyCodeForm'
import * as verifyApi from '../../api/verifyApi'

// The code-entry and submit half of VerifyCodeForm. The countdown and the resend button it gates
// live in VerifyCodeForm.resend.test.tsx — they need fake timers, which nothing here does.

vi.mock('../../api/verifyApi', async (importOriginal) => {
  const actual = await importOriginal<typeof verifyApi>()
  return { ...actual, verify: vi.fn() }
})

describe('VerifyCodeForm', () => {
  it('displays six single-digit code inputs', () => {
    renderWithRouter(<VerifyCodeForm />)

    for (let index = 0; index < 6; index += 1) {
      const input = screen.getByTestId(`verify-code-input-${index}`)
      expect(input).toHaveAttribute('type', 'text')
      expect(input).toHaveAttribute('inputMode', 'numeric')
      expect(input).toHaveAttribute('maxLength', '1')
    }
  })

  describe('digit auto-advance focus', () => {
    const expectOtherBoxesEmpty = (exceptIndex: number) => {
      for (let index = 0; index < 6; index += 1) {
        if (index === exceptIndex) continue
        expect((screen.getByTestId(`verify-code-input-${index}`) as HTMLInputElement).value).toBe(
          '',
        )
      }
    }

    it('advances focus to the next box and records the digit when a digit is typed', () => {
      renderWithRouter(<VerifyCodeForm />)

      const firstInput = screen.getByTestId('verify-code-input-0') as HTMLInputElement
      const secondInput = screen.getByTestId('verify-code-input-1')
      firstInput.focus()
      fireEvent.change(firstInput, { target: { value: '5' } })

      expect(firstInput.value).toBe('5')
      expect(document.activeElement).toBe(secondInput)
      expectOtherBoxesEmpty(0)
    })

    it('keeps focus on the last box and records the digit when its value is typed', () => {
      renderWithRouter(<VerifyCodeForm />)

      const lastInput = screen.getByTestId('verify-code-input-5') as HTMLInputElement
      lastInput.focus()
      fireEvent.change(lastInput, { target: { value: '9' } })

      expect(lastInput.value).toBe('9')
      expect(document.activeElement).toBe(lastInput)
      expectOtherBoxesEmpty(5)
    })
  })

  describe('confirm button', () => {
    it('disables the confirm button immediately after click', () => {
      // Needs a real call in flight to have an in-flight window at all: submit now returns
      // early when no email is known, so the pre-integration version of this test — which
      // rendered with no email — was asserting a disable driven by a placeholder's fake
      // timer, not by a request. The pending promise is held open deliberately.
      vi.mocked(verifyApi.verify).mockReturnValue(new Promise(() => {}))
      renderWithRouter(<VerifyCodeForm email="user@example.com" />)
      const confirmButton = screen.getByTestId('verify-confirm-button')
      expect(confirmButton).toHaveTextContent('Подтвердить')
      expect(confirmButton).not.toBeDisabled()

      fireEvent.click(confirmButton)

      expect(confirmButton).toBeDisabled()
    })
  })
})
