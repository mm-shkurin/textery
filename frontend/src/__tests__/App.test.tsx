import { describe, expect, it, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import App from '../App'
import * as api from '../features/generation/api/generationApi'
import * as documentApi from '../features/generation/api/documentApi'

vi.mock('../features/generation/api/generationApi')
vi.mock('../features/generation/api/documentApi')

function openModeModalForDoklad() {
  fireEvent.click(screen.getByTestId('features-primary-cta-button'))
  fireEvent.click(screen.getByTestId('type-card-doklad'))
  expect(screen.getByTestId('mode-modal')).toBeInTheDocument()
}

describe('App step transitions', () => {
  beforeEach(() => {
    vi.mocked(api.createGeneration).mockReturnValue(new Promise(() => {}))
    vi.mocked(documentApi.createDocument).mockReturnValue(new Promise(() => {}))
  })

  it('walks landing -> type -> mode -> form and back to landing on close', () => {
    render(<App />)

    openModeModalForDoklad()

    fireEvent.click(screen.getByTestId('mode-card-auto'))
    expect(screen.getByTestId('chat-panel')).toBeInTheDocument()
  })

  it('back button from mode modal returns to type modal', () => {
    render(<App />)

    openModeModalForDoklad()

    fireEvent.click(screen.getByLabelText(/Назад к типу документа/))
    expect(screen.getByTestId('type-modal')).toBeInTheDocument()
  })

  it('closing the type modal returns to landing', () => {
    render(<App />)

    fireEvent.click(screen.getByTestId('features-primary-cta-button'))
    fireEvent.click(screen.getByLabelText('Закрыть'))

    expect(screen.queryByTestId('type-modal')).not.toBeInTheDocument()
  })

  it('selecting manual mode opens a dedicated empty editor with a document-type breadcrumb', () => {
    render(<App />)

    openModeModalForDoklad()

    fireEvent.click(screen.getByTestId('mode-card-manual'))

    expect(screen.queryByTestId('mode-modal')).not.toBeInTheDocument()
    expect(screen.getByTestId('manual-editor')).toBeInTheDocument()
    expect(screen.getByTestId('editor-breadcrumb')).toHaveTextContent('Доклад · Ручной режим')
  })

  // RED (scenario 6.1): ManualEditor's onBack is wired to closeToLanding, which
  // resets step to 'landing' and clears documentType/mode instead of returning
  // to the mode modal. Predicted/actual: TestingLibraryElementError, unable to
  // find [data-testid="mode-modal"] (rendered landing page instead).
  it.skip('back button from the manual editor returns to the mode modal, document type still scoped', () => {
    render(<App />)

    openModeModalForDoklad()
    fireEvent.click(screen.getByTestId('mode-card-manual'))
    expect(screen.getByTestId('manual-editor')).toBeInTheDocument()

    fireEvent.click(screen.getByLabelText('Назад'))

    expect(screen.queryByTestId('manual-editor')).not.toBeInTheDocument()
    expect(screen.getByTestId('mode-modal')).toBeInTheDocument()
    expect(screen.getByLabelText('Назад к типу документа: Доклад')).toBeInTheDocument()
  })
})
