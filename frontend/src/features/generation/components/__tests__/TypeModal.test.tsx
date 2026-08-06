import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { TypeModal } from '../TypeModal'
import { SelectableCard } from '../SelectableCard'
import { DOCUMENT_TYPES } from '../../../../shared/documentTypes'

describe('TypeModal', () => {
  // Every type, not just доклад: with a single card the assertion passes against a modal that
  // reports the same id whichever card was clicked, which is exactly the defect that mattered
  // while three of the four were unreachable.
  it.each(DOCUMENT_TYPES.map((type) => type.id))(
    'selecting the %s card calls onSelect with its own id',
    (id) => {
      const onSelect = vi.fn()
      render(<TypeModal onSelect={onSelect} onClose={vi.fn()} />)

      const card = screen.getByTestId(`type-card-${id}`)
      expect(card).toBeEnabled()
      fireEvent.click(card)

      expect(onSelect).toHaveBeenCalledWith(id)
    },
  )

  // Asserted on `SelectableCard` directly rather than through the modal: all four types are
  // selectable today, so there is no unavailable card in `DOCUMENT_TYPES` to click. The
  // affordance still has to work — the next type specced before it can be generated will set
  // `available: false` again, and a mechanism nothing covers is a mechanism that has rotted by
  // then.
  it('an unavailable card is disabled and does not call onSelect', () => {
    const onSelect = vi.fn()
    render(
      <SelectableCard
        name="Эссе"
        available={false}
        cardClassName="type-card"
        nameClassName="type-card-name"
        testId="type-card-unavailable"
        onSelect={onSelect}
      />,
    )

    const card = screen.getByTestId('type-card-unavailable')
    expect(card).toBeDisabled()
    fireEvent.click(card)

    expect(onSelect).not.toHaveBeenCalled()
  })

  it('onClose fires when close button is clicked', () => {
    const onClose = vi.fn()
    render(<TypeModal onSelect={vi.fn()} onClose={onClose} />)

    fireEvent.click(screen.getByLabelText('Закрыть'))

    expect(onClose).toHaveBeenCalled()
  })
})
