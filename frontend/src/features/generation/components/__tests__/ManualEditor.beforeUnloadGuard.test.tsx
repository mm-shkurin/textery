import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import * as documentApi from '../../api/documentApi'
import { ManualEditor } from '../ManualEditor'
import { renderEditorWithDocumentCreated } from './ManualEditor.testSupport'

vi.mock('../../api/documentApi')

function dispatchBeforeUnload(): boolean {
  const event = new Event('beforeunload', { cancelable: true })
  window.dispatchEvent(event)
  return event.defaultPrevented
}

// The editor holds unsaved work only in Tiptap's in-memory state — closing or refreshing the tab
// loses it silently. The browser's one built-in defence is the beforeunload native prompt, shown
// only if a listener calls preventDefault. This guard must arm while the document is dirty, stand
// down once a save leaves it clean, and detach on unmount so a closed editor cannot block navigation.
describe('ManualEditor beforeunload guard', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.clearAllMocks()
  })

  it('prevents unload while the document is dirty', async () => {
    await renderEditorWithDocumentCreated()

    // The guard also sets `event.returnValue = ''`, which legacy Chrome/Edge and older Safari/Firefox
    // require to actually SHOW the native prompt. jsdom cannot pin that: its generic Event exposes only
    // the legacy boolean `returnValue` getter (`!defaultPrevented`), never the BeforeUnloadEvent string
    // form — so `returnValue === ''` is unobservable here. The live effect of returnValue is owed to a
    // Track B green-selenium prompt test; jsdom proves only that the guard cancels the event.
    expect(dispatchBeforeUnload()).toBe(true)
  })

  it('arms the guard while dirty then stands down once a save has resolved clean', async () => {
    await renderEditorWithDocumentCreated()

    const contentArea = screen.getByTestId('editor-content-area')
    contentArea.textContent = 'hello world'
    fireEvent.input(contentArea)

    // Load-bearing transition: prove the guard is ARMED while the edit is unsaved. Without this
    // pre-save assertion the post-save `false` could pass vacuously (guard never armed at all).
    expect(dispatchBeforeUnload()).toBe(true)

    vi.mocked(documentApi.saveDocument).mockResolvedValue({
      status: 'saved',
      version: 2,
      content: 'hello world',
    })

    fireEvent.click(screen.getByRole('button', { name: 'Сохранить' }))

    // The clean status below is the gate: hasUnsavedChanges initialises true, so without a settled
    // save the assertion would pass for the wrong reason. getByText throws until the save settles.
    await waitFor(() => {
      expect(screen.getByText('Сохранено')).toBeInTheDocument()
    })

    // ...and stands down once clean. This must be the transition true -> false, not a static false.
    expect(dispatchBeforeUnload()).toBe(false)
  })

  it('removes the exact listener it registered on unmount so a closed editor no longer blocks unload', async () => {
    const addSpy = vi.spyOn(window, 'addEventListener')
    const removeSpy = vi.spyOn(window, 'removeEventListener')
    vi.mocked(documentApi.createDocument).mockResolvedValue({
      documentId: 'doc-1',
      status: 'draft',
      version: 7,
    })
    const { unmount } = render(
      <ManualEditor documentType="doklad" documentTypeLabel="Доклад" onBack={vi.fn()} />,
    )
    await waitFor(() => {
      expect(screen.getByText('Черновик, ещё не сохранён')).toBeInTheDocument()
    })

    // Capture the exact handler reference registered for beforeunload. A fresh document initialises
    // dirty, so the guard must be armed here — proving there is a real listener to remove.
    const registered = addSpy.mock.calls.filter(([type]) => type === 'beforeunload')
    expect(registered).toHaveLength(1)
    const handler = registered[0][1]
    expect(dispatchBeforeUnload()).toBe(true)

    unmount()

    // Removal must target the SAME handler reference — not merely "a" beforeunload listener. This
    // fails if cleanup passes a different function (a common leak) or omits the removeEventListener.
    expect(removeSpy).toHaveBeenCalledWith('beforeunload', handler)
    // And behaviourally: the detached editor no longer prevents unload.
    expect(dispatchBeforeUnload()).toBe(false)
  })

  it('sets returnValue on the event so legacy browsers actually render the leave prompt', async () => {
    // Dispatching a synthetic Event only exposes the LEGACY boolean returnValue getter
    // (!defaultPrevented) — in jsdom AND real Chrome alike — so `dispatchBeforeUnload` above can
    // never observe the string assignment. But the guard's `event.returnValue = ''` is a plain
    // field write, and legacy Chrome/Edge + older Safari/Firefox only render the native prompt
    // when it is set. Calling the captured handler DIRECTLY with a mock event observes it — the
    // one place this otherwise-untested line (ManualEditor.tsx) has teeth. A refactor dropping
    // the assignment (silent no-prompt on those browsers) fails here.
    const addSpy = vi.spyOn(window, 'addEventListener')
    await renderEditorWithDocumentCreated()
    const registered = addSpy.mock.calls.filter(([type]) => type === 'beforeunload')
    expect(registered).toHaveLength(1)
    const handler = registered[0][1] as (event: BeforeUnloadEvent) => void

    const event = { preventDefault: vi.fn(), returnValue: undefined } as unknown as BeforeUnloadEvent
    handler(event)

    expect(event.preventDefault).toHaveBeenCalledTimes(1)
    expect(event.returnValue).toBe('')
  })
})
