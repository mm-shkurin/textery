import { describe, expect, it, vi } from 'vitest'
import { act, fireEvent, screen } from '@testing-library/react'
import * as documentApi from '../../api/documentApi'
import {
  AUTOSAVE_DEBOUNCE_MS,
  flushMicrotasks,
  typeIntoEditor,
  useAutosaveFakeTimers,
} from './ManualEditor.autosave.testSupport'
import {
  CREATED_DOCUMENT_ID,
  CREATED_VERSION,
  renderCreatedDocument,
} from './ManualEditor.autosaveRender.testSupport'

vi.mock('../../api/documentApi')

// Scenario H9.4, pre-condition (d) — the redundant trailing PUT reached through the MANUAL button,
// with no mid-flight edit involved at all. Typing arms the debounce; clicking Сохранить part-way
// through that window saves and marks the document clean, but nothing clears the armed timer, so the
// rest of the window elapses into a second PUT over content the server already has.
//
// The existing click-save tests run on real timers and never cross the boundary, so a guard scoped
// only to the autosave path would leave this live and the whole suite green.
const CLICK_AT_MS = 300

describe('ManualEditor — a manual save leaves no trailing autosave behind (H9.4 d)', () => {
  useAutosaveFakeTimers()

  it('does not fire a second saveDocument when the debounce armed before the click elapses', async () => {
    await renderCreatedDocument()

    vi.mocked(documentApi.saveDocument).mockResolvedValue({
      status: 'saved',
      version: 8,
      content: '<p>hello world</p>',
    })

    await typeIntoEditor('hello world')
    await act(async () => {
      await vi.advanceTimersByTimeAsync(CLICK_AT_MS)
    })

    fireEvent.click(screen.getByRole('button', { name: 'Сохранить' }))
    await flushMicrotasks()
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)
    expect(documentApi.saveDocument).toHaveBeenCalledWith(
      CREATED_DOCUMENT_ID,
      '<p>hello world</p>',
      CREATED_VERSION,
    )

    // Cross what remains of the window the keystroke armed: unchanged content, so nothing to write.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(AUTOSAVE_DEBOUNCE_MS)
    })
    await flushMicrotasks()
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)
  })
})
