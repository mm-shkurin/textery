import { describe, expect, it, vi } from 'vitest'
import { act, screen } from '@testing-library/react'
import * as documentApi from '../../api/documentApi'
import {
  AUTOSAVE_DEBOUNCE_MS,
  CREATED_DOCUMENT_ID,
  CREATED_VERSION,
  flushMicrotasks,
  renderCreatedDocument,
  typeIntoEditor,
  useAutosaveFakeTimers,
} from './ManualEditor.autosave.testSupport'

vi.mock('../../api/documentApi')

// Scenario E3.1 (07_Editor_Extension_Tests.md §3.1): edits autosave without an explicit click.
// Green will schedule a debounced save on edit. Assumed debounce interval: AUTOSAVE_DEBOUNCE_MS — a
// save must fire once the user stops typing past it, and must NOT fire before it (debounce, not
// save-on-every-keystroke). Assert around that constant.

describe('ManualEditor debounced autosave', () => {
  useAutosaveFakeTimers()

  it('autosaves an edit once typing stops past the debounce interval, without clicking Сохранить, and shows the saved indicator', async () => {
    await renderCreatedDocument()
    expect(screen.getByText('Черновик, ещё не сохранён')).toBeInTheDocument()

    vi.mocked(documentApi.saveDocument).mockResolvedValue({
      status: 'saved',
      version: 8,
      content: 'hello world',
    })

    await typeIntoEditor('hello world')

    // Before the debounce elapses: no autosave has fired yet.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(AUTOSAVE_DEBOUNCE_MS - 1)
    })
    expect(documentApi.saveDocument).not.toHaveBeenCalled()

    // Cross the debounce boundary by exactly one tick (now at AUTOSAVE_DEBOUNCE_MS):
    // the edit is saved automatically, no click. Landing exactly on the constant pins
    // the fire point to the debounce interval rather than "somewhere just after it".
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1)
    })
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)
    expect(documentApi.saveDocument).toHaveBeenCalledWith(
      CREATED_DOCUMENT_ID,
      '<p>hello world</p>',
      CREATED_VERSION,
    )

    await flushMicrotasks()
    expect(screen.getByText('Сохранено')).toBeInTheDocument()
  })

  // Guard: a burst of edits inside the window must collapse to ONE save. If the first edit's timer
  // were not cleared when the second lands, this run would fire twice — once for each edit. Proves
  // the clearTimeout-on-reschedule, not a per-keystroke save storm.
  it('collapses multiple edits within the debounce window into a single autosave', async () => {
    await renderCreatedDocument()

    vi.mocked(documentApi.saveDocument).mockResolvedValue({
      status: 'saved',
      version: 8,
      content: 'hello world',
    })

    await typeIntoEditor('hello')

    // Partway into the window, before the first edit's debounce elapses.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
    })
    expect(documentApi.saveDocument).not.toHaveBeenCalled()

    // A second edit resets the timer. The first edit's deadline (t=1000) now sits INSIDE the span we
    // advance below, so an uncleared first timer would fire there — producing a second call.
    await typeIntoEditor('hello world')

    // Advance a full debounce past the second edit (crossing t=1000 where the first would have fired).
    await act(async () => {
      await vi.advanceTimersByTimeAsync(AUTOSAVE_DEBOUNCE_MS)
    })
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)
  })

  // Guard: navigating away before the debounce elapses must cancel the pending autosave. Without the
  // timer clear in the hook's cleanup, the timer would fire after unmount — a write to an abandoned
  // document plus a state update on an unmounted component. Mirrors the beforeunload detach-on-unmount.
  it('cancels a pending autosave when the editor unmounts before the debounce elapses', async () => {
    const { unmount } = await renderCreatedDocument()

    await typeIntoEditor('hello world')

    unmount()

    // Advance well past the debounce: the cancelled timer must not fire a save.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(AUTOSAVE_DEBOUNCE_MS * 2)
    })
    expect(documentApi.saveDocument).not.toHaveBeenCalled()
  })
})
