import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { TypeModal } from '../TypeModal'
import { TypeCard } from '../TypeCard'
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

  // Asserted on `TypeCard` directly rather than through the modal: all four types are selectable
  // today, so there is no unavailable card in `DOCUMENT_TYPES` to click. The affordance still has
  // to work — the next type specced before it can be generated will set `available: false` again,
  // and a mechanism nothing covers is a mechanism that has rotted by then.
  it('an unavailable card is disabled and does not call onSelect', () => {
    const onSelect = vi.fn()
    render(
      <TypeCard
        option={{
          id: 'essay',
          name: 'Эссе',
          available: false,
          description: 'Личный взгляд на проблему',
        }}
        onSelect={onSelect}
      />,
    )

    const card = screen.getByTestId('type-card-essay')
    expect(card).toBeDisabled()
    fireEvent.click(card)

    expect(onSelect).not.toHaveBeenCalled()
  })

  // The card says what the type IS, not only what it is called. The modal shipped with four bare
  // names, which asks a user who has never written a доклад to pick between four words.
  it('names each type and says what it is', () => {
    render(<TypeModal onSelect={vi.fn()} onClose={vi.fn()} />)

    for (const option of DOCUMENT_TYPES) {
      const card = screen.getByTestId(`type-card-${option.id}`)
      expect(card).toHaveTextContent(option.name)
      expect(card).toHaveTextContent(option.description)
    }
  })

  // «Создание проекта» — the object this modal creates is called a project on the screen that
  // opens it, and it said «документа» here.
  it('is titled as the creation of a project', () => {
    render(<TypeModal onSelect={vi.fn()} onClose={vi.fn()} />)

    expect(screen.getByRole('heading', { name: 'Создание проекта' })).toBeInTheDocument()
  })

  it('onClose fires when close button is clicked', () => {
    const onClose = vi.fn()
    render(<TypeModal onSelect={vi.fn()} onClose={onClose} />)

    fireEvent.click(screen.getByLabelText('Закрыть'))

    expect(onClose).toHaveBeenCalled()
  })
})
