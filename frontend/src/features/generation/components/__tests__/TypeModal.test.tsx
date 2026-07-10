import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { TypeModal } from '../TypeModal'

describe('TypeModal', () => {
  it('selecting an available card calls onSelect with its id', () => {
    const onSelect = vi.fn()
    render(<TypeModal onSelect={onSelect} onClose={vi.fn()} />)

    fireEvent.click(screen.getByTestId('type-card-doklad'))

    expect(onSelect).toHaveBeenCalledWith('doklad')
  })

  it('disabled cards do not call onSelect', () => {
    const onSelect = vi.fn()
    render(<TypeModal onSelect={onSelect} onClose={vi.fn()} />)

    const essayCard = screen.getByTestId('type-card-essay')
    expect(essayCard).toBeDisabled()

    fireEvent.click(essayCard)

    expect(onSelect).not.toHaveBeenCalled()
  })

  it('onClose fires when close button is clicked', () => {
    const onClose = vi.fn()
    render(<TypeModal onSelect={vi.fn()} onClose={onClose} />)

    fireEvent.click(screen.getByLabelText('Закрыть'))

    expect(onClose).toHaveBeenCalled()
  })
})
