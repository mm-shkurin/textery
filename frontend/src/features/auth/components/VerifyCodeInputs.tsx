import { useRef } from 'react'

export const CODE_LENGTH = 6

interface VerifyCodeInputsProps {
  digits: string[]
  onChange: (digits: string[]) => void
}

// The six code boxes and everything that makes them behave like ONE field: advance on entry,
// step back on backspace, spread a pasted code across all six, and refuse non-digits.
//
// Split out of VerifyCodeForm, which was over the 200-line limit and mixed this input-behaviour
// state machine with submit orchestration and layout. The form now owns the code as a value; how
// six boxes conspire to produce it is this component's business.
export function VerifyCodeInputs({ digits, onChange }: VerifyCodeInputsProps) {
  const inputRefs = useRef<Array<HTMLInputElement | null>>([])

  // `inputMode="numeric"` is a keyboard HINT, not a constraint — a physical keyboard, an
  // autofill, or a paste puts anything it likes in the box. Non-digits earn a 400 INVALID_CODE
  // (verifyApi's header records the contract), so they are dropped here rather than spent on a
  // round-trip whose answer is already known.
  function handleChange(index: number, value: string) {
    const digit = value.replace(/\D/g, '').slice(-1)
    const next = [...digits]
    next[index] = digit
    onChange(next)

    if (digit && index < CODE_LENGTH - 1) {
      inputRefs.current[index + 1]?.focus()
    }
  }

  // Backspace in an empty box steps back a field. Without it the only way back is the mouse: the
  // caret has nowhere to go inside a maxLength=1 input that is already empty.
  function handleKeyDown(index: number, event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Backspace' && !digits[index] && index > 0) {
      inputRefs.current[index - 1]?.focus()
    }
  }

  // A code arrives as ONE string — from a password manager, or copied out of the dev-code line
  // this very screen prints. Default per-box paste would drop five of the six characters into a
  // field that keeps one, so the paste is spread across the boxes from wherever it landed.
  function handlePaste(index: number, event: React.ClipboardEvent<HTMLInputElement>) {
    const pasted = event.clipboardData.getData('text').replace(/\D/g, '')
    if (!pasted) return
    event.preventDefault()
    const next = [...digits]
    for (let offset = 0; offset < pasted.length && index + offset < CODE_LENGTH; offset++) {
      next[index + offset] = pasted[offset]
    }
    onChange(next)
    inputRefs.current[Math.min(index + pasted.length, CODE_LENGTH) - 1]?.focus()
  }

  return (
    // Grouped and named: six separate boxes are six anonymous text fields to a screen reader,
    // which cannot tell they are one code, nor which position it is on.
    //
    // <fieldset> rather than a div with role="group" — it is the element that means this, and
    // grouping form controls is the entire job it exists for. Named with aria-label instead of a
    // <legend>: a legend would render the words "Код подтверждения" a second time directly under
    // the h1 that already says them. The name is for the people who cannot see that h1.
    <fieldset className="verify-code-inputs" aria-label="Код подтверждения">
      {Array.from({ length: CODE_LENGTH }, (_, index) => (
        <input
          key={index}
          ref={(element) => {
            inputRefs.current[index] = element
          }}
          type="text"
          inputMode="numeric"
          // Only the first box claims the OTP: naming all six makes a browser offer to fill the
          // whole code into each one.
          autoComplete={index === 0 ? 'one-time-code' : 'off'}
          maxLength={1}
          value={digits[index]}
          aria-label={`Цифра ${index + 1} из ${CODE_LENGTH}`}
          onChange={(event) => handleChange(index, event.target.value)}
          onKeyDown={(event) => handleKeyDown(index, event)}
          onPaste={(event) => handlePaste(index, event)}
          data-testid={`verify-code-input-${index}`}
        />
      ))}
    </fieldset>
  )
}
