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
})
