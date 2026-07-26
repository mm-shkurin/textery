import { expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { ManualEditor } from '../ManualEditor'
import * as documentApi from '../../api/documentApi'

export async function renderEditorWithDocumentCreated(onBack = vi.fn()) {
  vi.mocked(documentApi.createDocument).mockResolvedValue({
    documentId: 'doc-1',
    status: 'draft',
    version: 7,
  })
  render(<ManualEditor documentType="doklad" documentTypeLabel="Доклад" onBack={onBack} />)
  await waitFor(() => {
    expect(screen.getByText('Черновик, ещё не сохранён')).toBeInTheDocument()
  })
  return onBack
}

// Reopen path: mounts <ManualEditor existingDocumentId=...> so useDocumentInit
// calls getDocument (not createDocument) and populates the editor via setContent.
// Waits until getDocument has been observed AND the content area is mounted, so the
// caller can assert the empty-state decoration once the reopen effect has settled.
export async function renderEditorReopeningDocument(content: string, onBack = vi.fn()) {
  vi.mocked(documentApi.getDocument).mockResolvedValue({
    documentId: 'doc-reopen',
    status: 'draft',
    content,
    version: 5,
  })
  render(
    <ManualEditor
      documentType="doklad"
      documentTypeLabel="Доклад"
      onBack={onBack}
      existingDocumentId="doc-reopen"
    />,
  )
  await waitFor(() => {
    expect(documentApi.getDocument).toHaveBeenCalledWith('doc-reopen')
  })
  return screen.getByTestId('editor-content-area')
}

// The block-schema editor renders an empty trailing paragraph as the cursor's
// landing block after a document that ends in a wrapper block (blockquote,
// codeBlock) or a heading; ProseMirror paints its empty last textblock with a
// cursor-helper <br>. It is stripped from the SAVED form (serializeEditorHtml)
// but present in the live rendered innerHTML, so block-conversion assertions
// that pin exact innerHTML include it.
export const TRAILING_BREAK_P = '<p><br class="ProseMirror-trailingBreak"></p>'

// After seeding text via `contentArea.textContent = ...; fireEvent.input`, the
// content auto-wraps into a paragraph, so the editable text lives one level
// deeper than the contenteditable root: root → <p> → text node.
export function paragraphTextNode(contentArea: HTMLElement): Node {
  return (contentArea.firstChild as HTMLElement).firstChild as Node
}

export function selectRange(node: Node, start: number, end: number) {
  const range = document.createRange()
  range.setStart(node, start)
  range.setEnd(node, end)
  const selection = window.getSelection()
  selection?.removeAllRanges()
  selection?.addRange(range)
}
