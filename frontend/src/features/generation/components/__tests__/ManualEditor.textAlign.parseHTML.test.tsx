import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ManualEditor } from '../ManualEditor'
import * as documentApi from '../../api/documentApi'
import { selectRange } from './ManualEditor.testSupport'

vi.mock('../../api/documentApi')

function renderReopenedEditor(content: string) {
  vi.mocked(documentApi.createDocument).mockResolvedValue({ documentId: 'doc-1', status: 'draft', version: 7 })
  vi.mocked(documentApi.getDocument).mockResolvedValue({
    documentId: 'doc-99',
    status: 'draft',
    content,
    version: 3,
  })

  render(
    <ManualEditor
      documentType="doklad"
      documentTypeLabel="Доклад"
      onBack={vi.fn()}
      existingDocumentId="doc-99"
    />
  )
}

describe('ManualEditor alignCenter parseHTML', () => {
  // This file has two tests sharing the module-level documentApi mock; without
  // a reset, getDocument's call count leaks between them and
  // toHaveBeenCalledExactlyOnceWith fails on the second.
  afterEach(() => {
    vi.clearAllMocks()
  })

  it('loading a saved document containing a centered <div> restores it as the alignCenter mark', async () => {
    renderReopenedEditor('before<div style="text-align: center">hello world</div>after')

    await waitFor(() => {
      expect(documentApi.getDocument).toHaveBeenCalledExactlyOnceWith('doc-99')
    })

    const contentArea = await screen.findByTestId('editor-content-area')
    await waitFor(() => {
      expect(contentArea.innerHTML).toBe(
        'before<div style="text-align: center">hello world</div>after'
      )
    })

    // Pins scenario 7.8's second clause: the toolbar button reflects the
    // restored alignment. Do NOT copy the sibling underline test's rationale
    // here ("innerHTML cannot tell an applied mark from raw passthrough") - it
    // does not hold: under this editor's `content: 'inline*'` schema no Node
    // owns `div`, so an unmatched wrapper is dropped rather than passed
    // through, as the false-branch test below proves. The innerHTML assertion
    // therefore already pins that getAttrs' true branch fired; this assertion
    // covers the user-visible highlight, which innerHTML says nothing about.
    const textNode = contentArea.childNodes[1].firstChild as Node
    selectRange(textNode, 1, 1)
    fireEvent.select(contentArea)

    expect(screen.getByTestId('toolbar-align-center')).toHaveAttribute('aria-pressed', 'true')
  })

  it('loading a saved document containing a plain <div> does not apply the alignCenter mark', async () => {
    renderReopenedEditor('before<div>hello world</div>after')

    await waitFor(() => {
      expect(documentApi.getDocument).toHaveBeenCalledExactlyOnceWith('doc-99')
    })

    // getAttrs' false branch: no text-align style, so the rule must decline
    // the match. With no Node type owning `div` under this editor's
    // `content: 'inline*'` schema, the wrapper is dropped and the text is
    // inlined unwrapped.
    const contentArea = await screen.findByTestId('editor-content-area')
    await waitFor(() => {
      expect(contentArea.innerHTML).toBe('beforehello worldafter')
    })

    const textNode = contentArea.firstChild as Node
    selectRange(textNode, 8, 8)
    fireEvent.select(contentArea)

    expect(screen.getByTestId('toolbar-align-center')).toHaveAttribute('aria-pressed', 'false')
  })
})
