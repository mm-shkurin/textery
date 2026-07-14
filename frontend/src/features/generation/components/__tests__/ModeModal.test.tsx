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

  // Removed: 'disabled manual mode does not call onSelect' asserted manual mode
  // was disabled — that contradicts Story 5 Scenario 1.1, which makes manual
  // mode available for every document type. The skipped test below is the
  // correct replacement specification for this card's behavior.

  it('selecting the available manual mode calls onSelect', () => {
    const onSelect = vi.fn()
    render(
      <ModeModal documentTypeLabel="Доклад" onSelect={onSelect} onBack={vi.fn()} onClose={vi.fn()} />,
    )

    const manualCard = screen.getByTestId('mode-card-manual')
    expect(manualCard).not.toBeDisabled()

    fireEvent.click(manualCard)

    expect(onSelect).toHaveBeenCalledWith('manual')
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
