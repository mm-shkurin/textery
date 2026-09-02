import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ManualEditorToolbar } from '../ManualEditorToolbar'

describe('ManualEditorToolbar', () => {
  it('disables every toolbar button when the editor instance is not yet ready', () => {
    render(<ManualEditorToolbar editor={null} />)

    expect(screen.getByTestId('toolbar-bold')).toBeDisabled()
    expect(screen.getByTestId('toolbar-strike')).toBeDisabled()
    expect(screen.getByTestId('toolbar-code')).toBeDisabled()
    expect(screen.getByTestId('toolbar-blockquote')).toBeDisabled()
    expect(screen.getByTestId('toolbar-horizontal-rule')).toBeDisabled()
    expect(screen.getByTestId('toolbar-code-block')).toBeDisabled()
    expect(screen.getByTestId('toolbar-undo')).toBeDisabled()
    expect(screen.getByTestId('toolbar-redo')).toBeDisabled()
  })

  // The block-schema migration (ADR 2026-07-26) enabled real block nodes, so
  // list controls became supported and were added (Scenario E2.1). The heading
  // level-1/2 and explicit paragraph controls remain absent: the schema exposes
  // only the H3 heading level, and there is no dedicated "paragraph" toggle —
  // showing those would overstate what the editor supports. They stay removed.
  it('renders the supported block controls and omits the ones the schema cannot back', () => {
    render(<ManualEditorToolbar editor={null} />)

    for (const label of ['Заголовок 1', 'Заголовок 2', 'Абзац']) {
      expect(screen.queryByLabelText(label)).toBeNull()
    }
    // The list controls now exist alongside the working inline controls.
    expect(screen.getByLabelText('Маркированный список')).toBeInTheDocument()
    expect(screen.getByLabelText('Нумерованный список')).toBeInTheDocument()
    expect(screen.getByTestId('toolbar-bold')).toBeInTheDocument()
    expect(screen.getByTestId('toolbar-h3')).toBeInTheDocument()
  })
})
