import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ManualEditorToolbar } from '../ManualEditorToolbar'

describe('ManualEditorToolbar', () => {
  it('disables every toolbar button when the editor instance is not yet ready', () => {
    render(
      <ManualEditorToolbar
        editor={null}
        documentId={null}
        hasUnsavedChanges={false}
        isSaving={false}
        onSave={vi.fn()}
      />,
    )

    expect(screen.getByTestId('toolbar-bold')).toBeDisabled()
    expect(screen.getByTestId('toolbar-strike')).toBeDisabled()
    expect(screen.getByTestId('toolbar-code')).toBeDisabled()
    expect(screen.getByTestId('toolbar-blockquote')).toBeDisabled()
    expect(screen.getByTestId('toolbar-horizontal-rule')).toBeDisabled()
    expect(screen.getByTestId('toolbar-code-block')).toBeDisabled()
    expect(screen.getByTestId('toolbar-undo')).toBeDisabled()
    expect(screen.getByTestId('toolbar-redo')).toBeDisabled()
  })

  // The inline-only document schema (Document.extend({ content: 'inline*' })) has no block
  // nodes, so toggleHeading / setParagraph / toggleBulletList / toggleOrderedList are inert —
  // clicking these controls does nothing. They were mockup-era stubs; showing them overstates
  // what the editor can do. Removed rather than left as dead surface.
  it('does not render the inert block controls the inline-only schema cannot support', () => {
    render(
      <ManualEditorToolbar
        editor={null}
        documentId={null}
        hasUnsavedChanges={false}
        isSaving={false}
        onSave={vi.fn()}
      />,
    )

    for (const label of ['Заголовок 1', 'Заголовок 2', 'Абзац', 'Маркированный список', 'Нумерованный список']) {
      expect(screen.queryByLabelText(label)).toBeNull()
    }
    // The working inline controls stay.
    expect(screen.getByTestId('toolbar-bold')).toBeInTheDocument()
    expect(screen.getByTestId('toolbar-h3')).toBeInTheDocument()
  })
})
