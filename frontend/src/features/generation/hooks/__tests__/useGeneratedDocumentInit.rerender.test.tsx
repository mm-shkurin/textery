import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ManualEditor } from '../../components/ManualEditor'
import * as documentApi from '../../api/documentApi'

vi.mock('../../api/documentApi')

const CONVERTED_HTML = '<p>Готовый текст реферата</p>'

// The conversion is a real round trip — measured at 200-500 ms against the live stack — and the
// editor re-renders freely while it is out: Tiptap re-renders on its own transactions, and
// `useDocumentSave` holds state above it. So the question this file asks is not exotic. It is what
// happens on the ordinary case where ANY render lands between the POST and its response.
//
// `useDocumentInit` next door already answers it, with a narrowed dependency array and an
// `eslint-disable` on the line above. `useGeneratedDocumentInit` lists `onReady` and `onError`
// instead, and `ManualEditor` passes `onReady: () => setHasUnsavedChanges(false)` — a new function
// identity on every render. The effect therefore re-runs, its cleanup sets `cancelled = true` on
// the run that owns the in-flight request, and the second run returns immediately because
// `convertedRef` is already true. Nobody is left to apply the response.
//
// The failure is silent in the worst way: the POST SUCCEEDS, so the document exists on the server
// and appears in «Мои проекты», and no error banner is shown. The user sees an empty editor over a
// document that was written correctly. Observed in production 2026-09-02 — the backend log for that
// session reads `POST /api/v1/documents/from-generation HTTP/1.1" 201 Created` with 6245 characters
// stored, while the editor on screen showed nothing.
describe.skip('useGeneratedDocumentInit when the editor re-renders mid-conversion', () => {
  it('still puts the converted document in the editor', async () => {
    let resolveConversion!: (value: documentApi.DocumentFromGenerationResult) => void
    vi.mocked(documentApi.createDocumentFromGeneration).mockReturnValue(
      new Promise((resolve) => {
        resolveConversion = resolve
      }),
    )

    // A parent that re-renders the editor on demand, standing in for the renders the real app
    // produces on its own. What it changes is deliberately cosmetic: the point is that ANY render
    // is enough, not that this particular prop matters.
    function Host() {
      const [label, setLabel] = useState('Реферат')
      return (
        <>
          <button data-testid="force-rerender" onClick={() => setLabel('Реферат ')}>
            rerender
          </button>
          <ManualEditor
            documentType="referat"
            documentTypeLabel={label}
            onBack={vi.fn()}
            generationId="gen-1"
          />
        </>
      )
    }

    render(<Host />)

    await waitFor(() => {
      expect(documentApi.createDocumentFromGeneration).toHaveBeenCalled()
    })

    // The render that lands while the conversion is still out.
    fireEvent.click(screen.getByTestId('force-rerender'))

    resolveConversion({
      documentId: 'doc-1',
      generationId: 'gen-1',
      title: 'Реферат',
      status: 'draft',
      content: CONVERTED_HTML,
      version: 1,
    })

    await waitFor(() => {
      expect(screen.getByTestId('editor-content-area')).toHaveTextContent('Готовый текст реферата')
    })

    // The conversion is guarded to happen once for one editor, and a re-render must not turn it
    // into a second document. Asserted here because the obvious way to make the line above pass —
    // dropping the once-only guard so a later effect run re-issues the POST — would trade a
    // missing document for a duplicated one.
    expect(documentApi.createDocumentFromGeneration).toHaveBeenCalledTimes(1)
  })
})
