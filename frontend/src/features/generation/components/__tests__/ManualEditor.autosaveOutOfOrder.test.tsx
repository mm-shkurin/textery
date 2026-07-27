import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, fireEvent, render, screen } from '@testing-library/react'
import { ManualEditor } from '../ManualEditor'
import * as documentApi from '../../api/documentApi'
import { AUTOSAVE_DEBOUNCE_MS, flushMicrotasks } from './ManualEditor.autosave.testSupport'

vi.mock('../../api/documentApi')

// Scenario E3.3 / H9.2 (07_Editor_Extension_Tests.md §3.3, 02_UI_Tests.md §4.2): two autosaves in
// flight resolving out of order — the shown status and content must reflect the LATEST edit (B),
// and a stale first (A) response must not overwrite the newer state.
//
// This is a LIVE CHARACTERIZATION GUARD, not a red→green cycle. useDocumentSave SERIALIZES saves:
// performSave sets isSavingRef; a save() or autosave landing mid-flight only flips
// saveAgainRequested rather than launching a second concurrent saveDocument. The queued save (B)
// is fired from A's resolve handler with A's returned version and a fresh read of the current
// editor content. So two saveDocument calls are NEVER simultaneously in flight through this path,
// and out-of-order ARRIVAL cannot occur — latest-wins holds by construction. There is nothing to
// implement, so green-frontend is [S]. This test locks the observable guarantee so a future change
// that let a stale A response clobber the newer content or status would fail here.

interface Deferred<T> {
  promise: Promise<T>
  resolve: (value: T) => void
}

function defer<T>(): Deferred<T> {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((res) => {
    resolve = res
  })
  return { promise, resolve }
}

describe('ManualEditor — out-of-order autosaves reflect the latest edit and content (E3.3/H9.2)', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.clearAllMocks()
    vi.useRealTimers()
  })

  it('keeps the latest edit and status when a queued save resolves after a stale first save, and the stale response never clobbers the newer content', async () => {
    vi.mocked(documentApi.createDocument).mockResolvedValue({
      documentId: 'doc-1',
      status: 'draft',
      version: 7,
    })
    render(<ManualEditor documentType="doklad" documentTypeLabel="Доклад" onBack={vi.fn()} />)
    await flushMicrotasks()

    // The first save (A) is held pending so a second edit lands while A is still "in flight".
    const saveA = defer<{ status: string; version: number; content: string }>()
    const saveB = defer<{ status: string; version: number; content: string }>()
    vi.mocked(documentApi.saveDocument)
      .mockReturnValueOnce(saveA.promise)
      .mockReturnValueOnce(saveB.promise)

    const contentArea = screen.getByTestId('editor-content-area')

    // Edit #1 → debounce → first autosave (A) fires and stays pending.
    contentArea.textContent = 'first version'
    await act(async () => {
      fireEvent.input(contentArea)
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(AUTOSAVE_DEBOUNCE_MS)
    })
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(1, 'doc-1', '<p>first version</p>', 7)

    // Edit #2 lands while A is still in flight: it must queue a re-save, NOT launch a second
    // concurrent saveDocument. Advancing the debounce here re-enters save() which finds A in
    // flight and only sets the "save again" flag.
    contentArea.textContent = 'second version'
    await act(async () => {
      fireEvent.input(contentArea)
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(AUTOSAVE_DEBOUNCE_MS)
    })
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)

    // A resolves LAST-in-wall-clock but FIRST-in-order, carrying stale server content that differs
    // from what the editor now holds. The resolve handler must NOT adopt it (editor moved on), and
    // must fire the queued save (B) with the LATEST content and A's returned version.
    await act(async () => {
      saveA.resolve({ status: 'saved', version: 8, content: '<p>STALE SERVER</p>' })
    })
    await flushMicrotasks()
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(2)
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(2, 'doc-1', '<p>second version</p>', 8)
    // The stale A response did not overwrite the editor's newer content.
    expect(screen.getByTestId('editor-content-area').innerHTML).toBe('<p>second version</p>')

    // B — the save for the latest edit — resolves and settles the shown state.
    await act(async () => {
      saveB.resolve({ status: 'saved', version: 9, content: '<p>second version</p>' })
    })
    await flushMicrotasks()

    // Final state reflects the latest edit (B): content preserved, status is exactly "saved".
    expect(screen.getByTestId('editor-content-area').innerHTML).toBe('<p>second version</p>')
    // Strict status: the saved element's own text is exactly "Сохранено" (not a substring hit
    // elsewhere), and the dirty status must be gone — a stale-A clobber reverting to dirty fails here.
    expect(screen.getByText('Сохранено').textContent).toBe('Сохранено')
    expect(screen.queryByText('Черновик, ещё не сохранён')).toBeNull()
  })
})
