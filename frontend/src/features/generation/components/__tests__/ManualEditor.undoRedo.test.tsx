import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import { renderEditorWithDocumentCreated } from './ManualEditor.testSupport'

vi.mock('../../api/documentApi')

// TDD Red Phase - toolbar-undo/toolbar-redo actions not implemented in TOOLBAR_ACTIONS
describe.skip('ManualEditor undo/redo toolbar', () => {
  it('disables the undo button when the editor has no changes to undo', async () => {
    await renderEditorWithDocumentCreated()

    const undoButton = screen.getByTestId('toolbar-undo')
    const redoButton = screen.getByTestId('toolbar-redo')

    expect(undoButton).toBeDisabled()
    expect(redoButton).toBeDisabled()
  })

  it('clicking undo after typing reverts the change and enables the redo button', async () => {
    await renderEditorWithDocumentCreated()

    const contentArea = screen.getByTestId('editor-content-area')
    contentArea.textContent = 'hello'
    fireEvent.input(contentArea)

    const undoButton = screen.getByTestId('toolbar-undo')
    const redoButton = screen.getByTestId('toolbar-redo')

    fireEvent.click(undoButton)

    expect(contentArea.textContent).toBe('')
    expect((redoButton as HTMLButtonElement).disabled).toBe(false)
  })

  it('clicking redo after an undo reapplies the reverted change and disables the redo button again', async () => {
    await renderEditorWithDocumentCreated()

    const contentArea = screen.getByTestId('editor-content-area')
    contentArea.textContent = 'hello'
    fireEvent.input(contentArea)

    const undoButton = screen.getByTestId('toolbar-undo')
    const redoButton = screen.getByTestId('toolbar-redo')

    fireEvent.click(undoButton)
    fireEvent.click(redoButton)

    expect(contentArea.textContent).toBe('hello')
    expect((redoButton as HTMLButtonElement).disabled).toBe(true)
  })
})
