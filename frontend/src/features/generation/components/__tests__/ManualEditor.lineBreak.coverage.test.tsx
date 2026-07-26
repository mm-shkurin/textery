import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ManualEditor } from '../ManualEditor'
import * as documentApi from '../../api/documentApi'
import { renderEditorWithDocumentCreated } from './ManualEditor.testSupport'

vi.mock('../../api/documentApi')

// Line-break coverage under the block schema (migration ADR, 2026-07-26, supersedes
// approach A′). Enter now SPLITS the block into a new paragraph; Shift+Enter inserts a
// hardBreak <br> within the block. These cases exercise both keymap paths, the trailing
// empty-paragraph strip (serializeEditorHtml), an interior break surviving, and a bare <br>
// in loaded content round-tripping without a parse error.
//
// The save payload asserted against is serializeEditorHtml(editor) — the trailing-empty-<p>
// stripped form — captured as the 2nd arg the saveDocument mock receives (useDocumentSave.ts).

// Each test renders its own editor; without this the module-level saveDocument mock keeps
// calls from earlier tests and calls[0] / toHaveBeenCalledTimes(1) would read the wrong save.
beforeEach(() => {
  vi.clearAllMocks()
})

function sentPayload() {
  return vi.mocked(documentApi.saveDocument).mock.calls[0][1]
}

function countBreaks(html: string) {
  return (html.match(/<br\s*\/?>/g) ?? []).length
}

async function saveAndGetPayload() {
  vi.mocked(documentApi.saveDocument).mockResolvedValue({
    status: 'saved',
    version: 8,
    content: 'ignored',
  })
  fireEvent.click(screen.getByRole('button', { name: 'Сохранить' }))
  await waitFor(() => expect(documentApi.saveDocument).toHaveBeenCalledTimes(1))
  return sentPayload()
}

// Every editing test renders a created-document editor and then targets its content area.
async function renderAndGetContentArea() {
  await renderEditorWithDocumentCreated()
  return screen.getByTestId('editor-content-area')
}

describe('ManualEditor line break — keymap and parse coverage', () => {
  // Case 1: a real Enter keystroke SPLITS the block into a new paragraph (block schema).
  // ProseMirror binds its keymap plugin to the editable element's keydown; @testing-library's
  // fireEvent.keyDown dispatches a real KeyboardEvent that the plugin's handleKeyDown reads.
  // Two lines separated by Enter persist as two <p> blocks, with no <br>.
  it('a real Enter keystroke splits the text into two paragraphs', async () => {
    const contentArea = await renderAndGetContentArea()

    contentArea.textContent = 'line one'
    fireEvent.input(contentArea)
    fireEvent.keyDown(contentArea, { key: 'Enter' })
    const secondParagraph = contentArea.lastChild as HTMLElement
    secondParagraph.textContent = 'line two'
    fireEvent.input(contentArea)

    const sent = await saveAndGetPayload()
    expect(sent).toBe('<p>line one</p><p>line two</p>')
    expect(countBreaks(sent)).toBe(0)
  })

  it('a Shift-Enter keystroke inserts exactly one <br>', async () => {
    const contentArea = await renderAndGetContentArea()

    fireEvent.keyDown(contentArea, { key: 'Enter', shiftKey: true })

    const sent = await saveAndGetPayload()
    expect(countBreaks(sent)).toBe(1)
  })

  // Case 2: typed non-empty content with NO trailing break — the ghost filler + cursor-helper
  // strip (hardBreakNode.ts) must keep the save payload free of any trailing <br> and of the
  // ProseMirror-trailingBreak helper class.
  it('typed content produces no stray trailing <br> in the save payload', async () => {
    const contentArea = await renderAndGetContentArea()
    contentArea.textContent = 'just one line'
    fireEvent.input(contentArea)

    const sent = await saveAndGetPayload()
    expect(/<br\s*\/?>\s*$/.test(sent)).toBe(false)
    expect(sent).not.toContain('ProseMirror-trailingBreak')
  })

  // Case 3: an INTENTIONAL Shift+Enter at the end of typed content keeps the trailing <br>
  // within the paragraph. Contrast with case 2's empty-editor filler strip: here the user
  // deliberately inserted a hardBreak after their text, so the <br> must survive into the
  // save payload. Driven through the real keymap (fireEvent.keyDown), which jsdom dispatches
  // to ProseMirror's keydown handler — the same path a browser keystroke takes.
  it('an intentional Shift-Enter at the end of typed content keeps the trailing <br>', async () => {
    const contentArea = await renderAndGetContentArea()
    contentArea.textContent = 'foo'
    fireEvent.input(contentArea)
    fireEvent.keyDown(contentArea, { key: 'Enter', shiftKey: true })

    const sent = await saveAndGetPayload()
    expect(sent).toContain('foo<br>')
    expect(countBreaks(sent)).toBe(1)
  })

  // Case 4: an interior break is not over-stripped — only the stray TRAILING break dies.
  it('an interior <br> between two lines survives', async () => {
    const contentArea = await renderAndGetContentArea()
    contentArea.innerHTML = 'line one<br>line two'
    fireEvent.input(contentArea)

    const sent = await saveAndGetPayload()
    expect(sent).toContain('line one<br>line two')
    expect(countBreaks(sent)).toBe(1)
  })
})

describe('ManualEditor line break — load round-trip', () => {
  // Case 5: a saved document whose content ends in a bare <br> loads through the init/reopen
  // path (getDocument -> setContent). HardBreakNode's parseHTML `{ tag: 'br' }` rule plus the
  // marker attribute's `parseHTML: () => 'br'` supply the required attr, so no
  // "No value supplied for attribute marker" parse error, and the break is preserved.
  it('loading content ending in a bare <br> preserves the break with no parse error', async () => {
    vi.mocked(documentApi.createDocument).mockResolvedValue({
      documentId: 'doc-1',
      status: 'draft',
      version: 7,
    })
    vi.mocked(documentApi.getDocument).mockResolvedValue({
      documentId: 'doc-99',
      status: 'draft',
      content: 'kept line<br>next',
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

    await waitFor(() => {
      expect(documentApi.getDocument).toHaveBeenCalledWith('doc-99')
    })

    const contentArea = await screen.findByTestId('editor-content-area')
    await waitFor(() => {
      expect(contentArea.innerHTML).toContain('kept line<br>next')
    })
    expect(countBreaks(contentArea.innerHTML)).toBe(1)
  })
})
