import { describe, expect, it, vi } from 'vitest'
import { act, screen } from '@testing-library/react'
import * as documentApi from '../../api/documentApi'
import {
  CREATED_DOCUMENT_ID,
  crossDebounceBoundary,
  defer,
  flushMicrotasks,
  renderCreatedDocument,
  typeIntoEditor,
  useAutosaveFakeTimers,
} from './ManualEditor.autosave.testSupport'

vi.mock('../../api/documentApi')

// Scenario H9.4, pre-condition (b)(1) — the dirty guard must be keyed on what the server CONFIRMED,
// not on what the client SENT. The server's copy is the sanitized one (it strips <script> with its
// contents and normalises void tags), and when the editor is idle the save handler adopts it. A
// guard keyed on the sent form would therefore never match the editor again after any sanitizing
// save, and the redundant trailing PUT would come straight back — as an idle loop, silently.
//
// Same shape as the trailing-PUT test, with one difference that decides it: the response content is
// NOT the bytes we sent. The opposite keying error — remembering content the editor holds but the
// server never received — is pinned from the data-loss side in
// ManualEditor.autosaveDirtyGuardQueuedFailure.test.tsx.
describe('ManualEditor — the trailing boundary is inert after a SANITIZING save (H9.4 b1)', () => {
  useAutosaveFakeTimers()

  it('does not re-save when the editor holds the adopted sanitized server content', async () => {
    await renderCreatedDocument()

    const firstSave = defer()
    vi.mocked(documentApi.saveDocument)
      .mockReturnValueOnce(firstSave.promise)
      // The queued mid-flight re-save comes back sanitized: same words, server-normalised markup.
      .mockResolvedValue({ status: 'saved', version: 9, content: '<p>hello <em>world</em></p>' })

    await typeIntoEditor('hello')
    await crossDebounceBoundary()

    // Edit #2 mid-flight: queues the re-save and arms the debounce deadline nothing later clears.
    await typeIntoEditor('hello world')
    await act(async () => {
      firstSave.resolve({ status: 'saved', version: 8, content: '<p>hello</p>' })
    })
    await flushMicrotasks()

    // The queued re-save resolved and its sanitized content was adopted into the editor. Adopting
    // it emits one more update, which sends the server's own form straight back (call #3, measured
    // 2026-07-27) — that echo settles against an identical response and stops there. What matters
    // for the guard is that the editor now holds the server's form, NOT the bytes it sent.
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(3)
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(
      3,
      CREATED_DOCUMENT_ID,
      '<p>hello <em>world</em></p>',
      9,
    )
    expect(screen.getByTestId('editor-content-area').innerHTML).toBe('<p>hello <em>world</em></p>')

    // Crossing the stale deadline must write nothing: the editor and the server already agree.
    await crossDebounceBoundary()
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(3)
    expect(screen.getByTestId('editor-content-area').innerHTML).toBe('<p>hello <em>world</em></p>')
  })
})
