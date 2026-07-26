import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import { renderEditorWithDocumentCreated } from './ManualEditor.testSupport'

vi.mock('../../api/documentApi')

describe('ManualEditor export control', () => {
  it('shows a PDF choice and a DOCX choice when the export control is opened', async () => {
    await renderEditorWithDocumentCreated()

    fireEvent.click(screen.getByTestId('export-control-trigger'))

    // Exact-match regexes, not substrings: the export endpoint accepts format=pdf|docx,
    // so the two choices must read exactly "PDF" and "DOCX" — "Скачать PDF" or "PDF ▾"
    // must not pass. Mirrors the acceptance statements' exact-label assertion.
    expect(screen.getByTestId('export-option-pdf')).toHaveTextContent(/^PDF$/)
    expect(screen.getByTestId('export-option-docx')).toHaveTextContent(/^DOCX$/)
  })
})
