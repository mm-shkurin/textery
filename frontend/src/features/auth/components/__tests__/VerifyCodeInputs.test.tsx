import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { CODE_LENGTH, VerifyCodeInputs } from '../VerifyCodeInputs'

// The six boxes behave like ONE field, and every rule that makes them do so — advance on entry,
// step back on backspace, spread a paste, drop non-digits — lived only in a comment: the
// component sat at 46% coverage because the VerifyCodeForm tests drive the code as a value and
// never exercise the box-level state machine. Each case below pins one of those rules.
function renderInputs(digits: string[] = Array(CODE_LENGTH).fill(''), hasError = false) {
  const onChange = vi.fn()
  render(<VerifyCodeInputs digits={digits} onChange={onChange} hasError={hasError} />)
  return { onChange }
}

function box(index: number): HTMLInputElement {
  return screen.getByTestId(`verify-code-input-${index}`) as HTMLInputElement
}

describe('VerifyCodeInputs', () => {
  it('renders exactly six boxes grouped under one accessible name', () => {
    renderInputs()

    expect(screen.getByRole('group', { name: 'Код подтверждения' })).toBeInTheDocument()
    expect(screen.getAllByRole('textbox')).toHaveLength(CODE_LENGTH)
  })

  // Only the first box claims the OTP; naming all six makes a browser fill the whole code into
  // each one.
  it('claims the one-time-code autofill on the first box only', () => {
    renderInputs()

    expect(box(0)).toHaveAttribute('autocomplete', 'one-time-code')
    expect(box(1)).toHaveAttribute('autocomplete', 'off')
  })

  it('writes the typed digit at its own index and moves focus forward', () => {
    const { onChange } = renderInputs()

    fireEvent.change(box(0), { target: { value: '4' } })

    expect(onChange).toHaveBeenCalledWith(['4', '', '', '', '', ''])
    expect(document.activeElement).toBe(box(1))
  })

  // `inputMode="numeric"` is a keyboard hint, not a constraint — a paste or a physical keyboard
  // puts anything in the box. A non-digit earns a 400 INVALID_CODE, so it is dropped here.
  it('drops a non-digit instead of spending a round trip on it', () => {
    const { onChange } = renderInputs()

    fireEvent.change(box(0), { target: { value: 'a' } })

    expect(onChange).toHaveBeenCalledWith(['', '', '', '', '', ''])
    expect(document.activeElement).not.toBe(box(1))
  })

  it('keeps only the last character when a box already holds a digit', () => {
    const { onChange } = renderInputs(['1', '', '', '', '', ''])

    fireEvent.change(box(0), { target: { value: '17' } })

    expect(onChange).toHaveBeenCalledWith(['7', '', '', '', '', ''])
  })

  it('does not advance past the final box', () => {
    renderInputs()
    box(CODE_LENGTH - 1).focus()

    fireEvent.change(box(CODE_LENGTH - 1), { target: { value: '9' } })

    expect(document.activeElement).toBe(box(CODE_LENGTH - 1))
  })

  // Backspace in an EMPTY box steps back; the caret inside a maxLength=1 field has nowhere else
  // to go, so without this the only way back is the mouse.
  it('steps focus back on backspace in an empty box', () => {
    renderInputs(['1', '', '', '', '', ''])

    fireEvent.keyDown(box(1), { key: 'Backspace' })

    expect(document.activeElement).toBe(box(0))
  })

  it('leaves focus alone when backspacing a box that still holds a digit', () => {
    renderInputs(['1', '2', '', '', '', ''])
    box(1).focus()

    fireEvent.keyDown(box(1), { key: 'Backspace' })

    expect(document.activeElement).toBe(box(1))
  })

  it('does not step back from the first box', () => {
    renderInputs()
    box(0).focus()

    fireEvent.keyDown(box(0), { key: 'Backspace' })

    expect(document.activeElement).toBe(box(0))
  })

  it('ignores keys other than backspace', () => {
    renderInputs()
    box(1).focus()

    fireEvent.keyDown(box(1), { key: 'ArrowLeft' })

    expect(document.activeElement).toBe(box(1))
  })

  // A code arrives as ONE string from a password manager. Default per-box paste would drop five
  // of six characters into a field that keeps one.
  it('spreads a pasted code across every box and focuses the last filled one', () => {
    const { onChange } = renderInputs()

    fireEvent.paste(box(0), { clipboardData: { getData: () => '123456' } })

    expect(onChange).toHaveBeenCalledWith(['1', '2', '3', '4', '5', '6'])
    expect(document.activeElement).toBe(box(CODE_LENGTH - 1))
  })

  it('spreads a paste from wherever it landed, not always from the first box', () => {
    const { onChange } = renderInputs(['9', '', '', '', '', ''])

    fireEvent.paste(box(1), { clipboardData: { getData: () => '12' } })

    expect(onChange).toHaveBeenCalledWith(['9', '1', '2', '', '', ''])
    expect(document.activeElement).toBe(box(2))
  })

  it('truncates a paste longer than the remaining boxes rather than overflowing', () => {
    const { onChange } = renderInputs()

    fireEvent.paste(box(4), { clipboardData: { getData: () => '123456' } })

    expect(onChange).toHaveBeenCalledWith(['', '', '', '', '1', '2'])
  })

  it('strips non-digits out of a pasted string', () => {
    const { onChange } = renderInputs()

    fireEvent.paste(box(0), { clipboardData: { getData: () => '12-34 56' } })

    expect(onChange).toHaveBeenCalledWith(['1', '2', '3', '4', '5', '6'])
  })

  it('ignores a paste that carries no digits at all', () => {
    const { onChange } = renderInputs()

    fireEvent.paste(box(0), { clipboardData: { getData: () => 'код' } })

    expect(onChange).not.toHaveBeenCalled()
  })

  // The form owns WHEN (it saw the rejection); this component owns how the boxes look.
  it('paints every box with the error class when the form reports a rejection', () => {
    renderInputs(Array(CODE_LENGTH).fill('1'), true)

    for (let index = 0; index < CODE_LENGTH; index++) {
      expect(box(index)).toHaveClass('error')
    }
  })

  it('leaves the boxes unpainted by default', () => {
    renderInputs()

    expect(box(0)).not.toHaveClass('error')
  })
})
