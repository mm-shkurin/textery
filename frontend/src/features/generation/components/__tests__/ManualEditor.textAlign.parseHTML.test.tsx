import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ManualEditor } from '../ManualEditor'
import * as documentApi from '../../api/documentApi'
import { selectRange } from './ManualEditor.testSupport'

vi.mock('../../api/documentApi')

function renderReopenedEditor(content: string) {
  vi.mocked(documentApi.createDocument).mockResolvedValue({
    documentId: 'doc-1',
    status: 'draft',
    version: 7,
  })
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
    />,
  )
}

describe('ManualEditor textAlign parseHTML', () => {
  // This file has two tests sharing the module-level documentApi mock; without
  // a reset, getDocument's call count leaks between them and
  // toHaveBeenCalledExactlyOnceWith fails on the second.
  afterEach(() => {
    vi.clearAllMocks()
  })

  it('loading a saved paragraph with text-align: center restores its centered alignment', async () => {
    // Block schema: alignment is a `textAlign` block attribute rendered as a
    // `style="text-align: …"` on the paragraph/heading itself (the old wrapping
    // <div> mark is retired). A saved centered paragraph round-trips as such;
    // jsdom re-serialises the style with a trailing semicolon.
    renderReopenedEditor('<p>before</p><p style="text-align: center">hello world</p><p>after</p>')

    await waitFor(() => {
      expect(documentApi.getDocument).toHaveBeenCalledExactlyOnceWith(
        'doc-99',
        expect.any(AbortSignal),
      )
    })

    const contentArea = await screen.findByTestId('editor-content-area')
    await waitFor(() => {
      expect(contentArea.innerHTML).toBe(
        '<p>before</p><p style="text-align: center;">hello world</p><p>after</p>',
      )
    })

    // Pins that the toolbar button reflects the restored alignment: a collapsed
    // cursor inside the centered paragraph lights the align-center control.
    const textNode = contentArea.childNodes[1].firstChild as Node
    selectRange(textNode, 1, 1)
    fireEvent.select(contentArea)

    expect(screen.getByTestId('toolbar-align-center')).toHaveAttribute('aria-pressed', 'true')
  })

  it('loading a saved paragraph with no alignment does not light the align-center control', async () => {
    // False branch: a plain paragraph carries no textAlign attribute, so the
    // align-center control stays inactive at a cursor inside it.
    renderReopenedEditor('<p>before</p><p>hello world</p><p>after</p>')

    await waitFor(() => {
      expect(documentApi.getDocument).toHaveBeenCalledExactlyOnceWith(
        'doc-99',
        expect.any(AbortSignal),
      )
    })

    const contentArea = await screen.findByTestId('editor-content-area')
    await waitFor(() => {
      expect(contentArea.innerHTML).toBe('<p>before</p><p>hello world</p><p>after</p>')
    })

    const textNode = contentArea.childNodes[1].firstChild as Node
    selectRange(textNode, 1, 1)
    fireEvent.select(contentArea)

    expect(screen.getByTestId('toolbar-align-center')).toHaveAttribute('aria-pressed', 'false')
  })
})
