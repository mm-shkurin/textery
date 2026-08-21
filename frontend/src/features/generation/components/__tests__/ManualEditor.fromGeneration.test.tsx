import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import * as documentApi from '../../api/documentApi'
import { ManualEditor } from '../ManualEditor'

// Explicit factory rather than an auto-mock: the frozen ES module namespace cannot take a runtime
// mock after import, so every function this path consumes is declared here.
vi.mock('../../api/documentApi', () => ({
  createDocument: vi.fn(),
  createDocumentFromGeneration: vi.fn(),
  getDocument: vi.fn(),
  saveDocument: vi.fn(),
  exportDocument: vi.fn(),
}))

const GENERATION_ID = 'gen-42'
const DOCUMENT_ID = 'doc-42'
// What the server stores: the model's markdown already converted and sanitized. The `#` characters
// are gone by the time anything reaches the editor — that conversion is the whole point.
const CONVERTED_HTML = '<h1>Доклад</h1><h2>Введение</h2><p>Первый абзац.</p>'

function renderGeneratedEditor() {
  return render(
    <ManualEditor
      documentType="doklad"
      documentTypeLabel="Доклад"
      onBack={() => {}}
      generationId={GENERATION_ID}
    />,
  )
}

describe('ManualEditor on the auto path — a generation becomes an editable document', () => {
  it('fills the editor from the conversion response and never re-reads the document', async () => {
    vi.mocked(documentApi.createDocumentFromGeneration).mockResolvedValue({
      documentId: DOCUMENT_ID,
      generationId: GENERATION_ID,
      title: 'Доклад',
      status: 'draft',
      content: CONVERTED_HTML,
      version: 1,
    })

    renderGeneratedEditor()

    const area = await screen.findByTestId('editor-content-area')
    await waitFor(() => expect(area.querySelector('h1')).toBeInstanceOf(HTMLHeadingElement))

    // Real block elements, not text that merely LOOKS converted: `toHaveTextContent` would pass on
    // a literal "# Доклад" string, which is exactly the bug this path exists to fix.
    expect(area.querySelector('h1')?.textContent).toBe('Доклад')
    expect(area.querySelector('h2')?.textContent).toBe('Введение')
    expect(area.textContent).not.toContain('#')

    expect(documentApi.createDocumentFromGeneration).toHaveBeenCalledWith(
      GENERATION_ID,
      expect.any(String),
    )
    // Scenario 2.3: the editor is populated from the conversion RESPONSE. A follow-up GET on a
    // multi-instance backend can land on an instance that has not seen the insert yet, and the
    // editor would open empty on text that is already stored.
    expect(documentApi.getDocument).not.toHaveBeenCalled()
    // And the auto path must not mint a second, empty document alongside the converted one.
    expect(documentApi.createDocument).not.toHaveBeenCalled()
  })

  it('reports the converted document as saved, not as an unsaved draft', async () => {
    // THE REGRESSION, observed against the live stack 2026-07-31, and the reason the editor is no
    // longer seeded with the generation's raw markdown. Seeding marked the document dirty; the
    // autosave debounce then wrote that RAW markdown straight over the converted HTML the server
    // had just stored, leaving the editor showing `## Введение` as plain text and the row
    // overwritten to match (version 2, markdown content).
    //
    // Asserted through the status line rather than through `saveDocument` not being called: the
    // absence of a call also holds when nothing armed a save at all, so it passes for the wrong
    // reason. The badge is a positive statement — the editor holds exactly what the server holds —
    // and it is the same flag that arms beforeunload and gates the autosave.
    vi.mocked(documentApi.createDocumentFromGeneration).mockResolvedValue({
      documentId: DOCUMENT_ID,
      generationId: GENERATION_ID,
      title: 'Доклад',
      status: 'draft',
      content: CONVERTED_HTML,
      version: 1,
    })

    renderGeneratedEditor()

    expect(await screen.findByText('Сохранено')).toBeInTheDocument()
    expect(screen.queryByText('Черновик, ещё не сохранён')).toBeNull()
  })
})
