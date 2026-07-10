import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { ModeModal } from '../ModeModal'

describe('ModeModal', () => {
  it('selecting the available auto mode calls onSelect', () => {
    const onSelect = vi.fn()
    render(
      <ModeModal documentTypeLabel="Доклад" onSelect={onSelect} onBack={vi.fn()} onClose={vi.fn()} />,
    )

    fireEvent.click(screen.getByTestId('mode-card-auto'))

    expect(onSelect).toHaveBeenCalledWith('auto')
  })

  it('disabled manual mode does not call onSelect', () => {
    const onSelect = vi.fn()
    render(
      <ModeModal documentTypeLabel="Доклад" onSelect={onSelect} onBack={vi.fn()} onClose={vi.fn()} />,
    )

    const manualCard = screen.getByTestId('mode-card-manual')
    expect(manualCard).toBeDisabled()

    fireEvent.click(manualCard)

    expect(onSelect).not.toHaveBeenCalled()
  })

  it('onBack fires when back button is clicked', () => {
    const onBack = vi.fn()
    render(
      <ModeModal documentTypeLabel="Доклад" onSelect={vi.fn()} onBack={onBack} onClose={vi.fn()} />,
    )

    fireEvent.click(screen.getByLabelText(/Назад к типу документа/))

    expect(onBack).toHaveBeenCalled()
  })
})
