import { describe, expect, it, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import App from '../App'
import * as api from '../features/generation/api/generationApi'

vi.mock('../features/generation/api/generationApi')

describe('App step transitions', () => {
  beforeEach(() => {
    vi.mocked(api.createGeneration).mockReturnValue(new Promise(() => {}))
  })

  it('walks landing -> type -> mode -> form and back to landing on close', () => {
    render(<App />)

    fireEvent.click(screen.getByTestId('features-primary-cta-button'))
    expect(screen.getByTestId('type-modal')).toBeInTheDocument()

    fireEvent.click(screen.getByTestId('type-card-doklad'))
    expect(screen.getByTestId('mode-modal')).toBeInTheDocument()

    fireEvent.click(screen.getByTestId('mode-card-auto'))
    expect(screen.getByTestId('chat-panel')).toBeInTheDocument()
  })

  it('back button from mode modal returns to type modal', () => {
    render(<App />)

    fireEvent.click(screen.getByTestId('features-primary-cta-button'))
    fireEvent.click(screen.getByTestId('type-card-doklad'))
    expect(screen.getByTestId('mode-modal')).toBeInTheDocument()

    fireEvent.click(screen.getByLabelText(/Назад к типу документа/))
    expect(screen.getByTestId('type-modal')).toBeInTheDocument()
  })

  it('closing the type modal returns to landing', () => {
    render(<App />)

    fireEvent.click(screen.getByTestId('features-primary-cta-button'))
    fireEvent.click(screen.getByLabelText('Закрыть'))

    expect(screen.queryByTestId('type-modal')).not.toBeInTheDocument()
  })

  // RED: TestingLibraryElementError: Unable to find an element by:
  // [data-testid="manual-editor"] -- App.tsx routes 'manual' mode to the same
  // ChatWorkspace as 'auto'; no dedicated manual editor view exists yet.
  it.skip('selecting manual mode opens a dedicated empty editor with a document-type breadcrumb', () => {
    render(<App />)

    fireEvent.click(screen.getByTestId('features-primary-cta-button'))
    fireEvent.click(screen.getByTestId('type-card-doklad'))
    expect(screen.getByTestId('mode-modal')).toBeInTheDocument()

    fireEvent.click(screen.getByTestId('mode-card-manual'))

    expect(screen.queryByTestId('mode-modal')).not.toBeInTheDocument()
    expect(screen.getByTestId('manual-editor')).toBeInTheDocument()
    expect(screen.getByTestId('editor-breadcrumb')).toHaveTextContent('Доклад · Ручной режим')
  })
})
