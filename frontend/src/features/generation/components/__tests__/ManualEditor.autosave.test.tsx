import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, fireEvent, render, screen } from '@testing-library/react'
import { ManualEditor } from '../ManualEditor'
import * as documentApi from '../../api/documentApi'

vi.mock('../../api/documentApi')

// Scenario E3.1 (07_Editor_Extension_Tests.md §3.1): edits autosave without an explicit click.
// Green will schedule a debounced save on edit. Assumed debounce interval: 1000ms — a save must
// fire once the user stops typing past it, and must NOT fire before it (debounce, not
// save-on-every-keystroke). Assert around that constant.
const AUTOSAVE_DEBOUNCE_MS = 1000

async function flushMicrotasks() {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(0)
  })
}

describe('ManualEditor debounced autosave', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.clearAllMocks()
    vi.useRealTimers()
  })

  it.skip('autosaves an edit once typing stops past the debounce interval, without clicking Сохранить, and shows the saved indicator', async () => {
    vi.mocked(documentApi.createDocument).mockResolvedValue({
      documentId: 'doc-1',
      status: 'draft',
      version: 7,
    })
    render(<ManualEditor documentType="doklad" documentTypeLabel="Доклад" onBack={vi.fn()} />)
    await flushMicrotasks()
    expect(screen.getByText('Черновик, ещё не сохранён')).toBeInTheDocument()

    vi.mocked(documentApi.saveDocument).mockResolvedValue({
      status: 'saved',
      version: 8,
      content: 'hello world',
    })

    const contentArea = screen.getByTestId('editor-content-area')
    contentArea.textContent = 'hello world'
    await act(async () => {
      fireEvent.input(contentArea)
    })

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
    expect(documentApi.saveDocument).toHaveBeenCalledWith('doc-1', '<p>hello world</p>', 7)

    await flushMicrotasks()
    expect(screen.getByText('Сохранено')).toBeInTheDocument()
  })
})
