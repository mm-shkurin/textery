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

export function selectRange(node: Node, start: number, end: number) {
  const range = document.createRange()
  range.setStart(node, start)
  range.setEnd(node, end)
  const selection = window.getSelection()
  selection?.removeAllRanges()
  selection?.addRange(range)
}
