import { describe, expect, it, vi } from 'vitest'
import * as documentApi from '../../api/documentApi'
import {
  CREATED_VERSION,
  defer,
  editorContentHtml,
  renderCreatedDocument,
  typeAndFireAutosave,
  typeIntoEditor,
  useAutosaveFailureFakeTimers,
} from './ManualEditor.autosave.testSupport'
import {
  PRODUCTION_SERVER_ERROR,
  SAVED_CONTENT,
  SAVED_PLAIN,
  expectAbandonmentRecorded,
  expectNoAbandonmentRecorded,
} from './ManualEditor.autosaveFixture'
import { dispatchBeforeUnload } from './ManualEditor.saveStatus.testSupport'

vi.mock('../../api/documentApi')

// The two directions the scenario's own RED cannot see. It unmounts at ONE instant — inside a
// backoff gap, with a timer object pending — and asserts the abandonment record appears. That
// leaves both neighbours open:
//
//   - UNCONDITIONALLY logging in the []-scoped cleanup passes it exactly, and then every ordinary
//     back-out of a fully-saved document writes a false abandonment into the app's only diagnostic
//     sink. The existing unmount test (ManualEditor.autosave.test.tsx) does not spy console.error.
//   - keying the record on "a retry timer exists" passes it too, and misses the FOUR in-flight
//     request sub-windows the same ~7-second ladder contains, where retryTimerRef is null and the
//     write is just as abandoned. The record has to key on "there is an unfinished write".

describe('ManualEditor — what the abandonment record must and must not say (H9.4 guards)', () => {
  useAutosaveFailureFakeTimers()

  it('records the abandonment when the editor unmounts with a request still in flight', async () => {
    const { unmount } = await renderCreatedDocument()
    // Never settles: the unmount lands INSIDE a request, not inside a backoff gap. No timer object
    // exists at this moment, and the write is nonetheless gone the instant the component dies.
    vi.mocked(documentApi.saveDocument).mockReturnValue(defer().promise)

    await typeAndFireAutosave(SAVED_PLAIN)
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)
    // Provably unpersisted at the moment we walk away — the app's own guard is armed.
    expect(dispatchBeforeUnload()).toBe(true)

    unmount()

    expectAbandonmentRecorded()
  })

  it('records nothing when the editor unmounts with every write settled', async () => {
    const { unmount } = await renderCreatedDocument()
    vi.mocked(documentApi.saveDocument).mockResolvedValue({
      status: 'saved',
      version: CREATED_VERSION + 1,
      content: `<p>${SAVED_PLAIN}</p>`,
    })

    await typeAndFireAutosave(SAVED_PLAIN)
    // Nothing is pending: the document is clean, so the browser guard has stood down.
    expect(dispatchBeforeUnload()).toBe(false)

    unmount()

    // The negative twin. console.error is the whole of this app's diagnostics; a record written on
    // every ordinary in-app back-out is how the one that matters becomes invisible.
    expectNoAbandonmentRecorded()
  })

  it('records the abandonment once, not once per failed attempt already logged', async () => {
    const { unmount } = await renderCreatedDocument()
    vi.mocked(documentApi.saveDocument).mockRejectedValue(PRODUCTION_SERVER_ERROR)

    await typeAndFireAutosave(SAVED_PLAIN)
    // Attempt 1's own rejection diagnostic belongs to the attempt, not to the abandonment.
    vi.mocked(console.error).mockClear()

    unmount()

    expectAbandonmentRecorded()
  })

  // The THIRD window, and the only one an ordinary user reaches without a 5xx first: the debounce
  // gap. `useAbandonedSaveRecord` keys the record on isSavingRef, which a debounced edit has not set
  // yet — the save has been decided on but not started. useAutosave's own []-scoped cleanup drops
  // that timer in silence. ManualEditor.autosave.test.tsx:94 already proves the drop and asserts only
  // that no save fired; it does not spy console.error, so the silence is nobody's assertion.
  //
  // RED 2026-07-29: fails inside expectAbandonmentRecorded(), at
  // `expect(console.error).toHaveBeenCalledTimes(1)`, with
  // `expected "error" to be called 1 times, but got 0 times`.
  it.skip('records the abandonment when the editor unmounts inside the debounce gap', async () => {
    const { unmount } = await renderCreatedDocument()

    // One edit, and the clock stays put — strictly inside AUTOSAVE_DEBOUNCE_MS. Nothing has been
    // sent, so isSavingRef was never set; the edit exists only as a pending timer.
    await typeIntoEditor(SAVED_PLAIN)
    expect(documentApi.saveDocument).not.toHaveBeenCalled()
    // The edit is REAL and it is exactly the one this case names — the editor holds the typed
    // paragraph, not merely an input event that fired. `dispatchBeforeUnload()` below cannot say
    // this: its twin proves it reads true with nothing typed at all, so on its own it pins the
    // case to a fact that is true in every window, including the one with nothing to abandon.
    expect(editorContentHtml()).toBe(SAVED_CONTENT)
    expect(dispatchBeforeUnload()).toBe(true)

    unmount()

    expectAbandonmentRecorded()
  })

  // The debounce path's negative twin, and the guard that stops the cheap green — "log in the
  // cleanup unconditionally" satisfies the case above and then writes a false abandonment on every
  // back-out of an untouched document. Nothing was ever typed here: no timer, no request, nothing to
  // abandon.
  //
  // The beforeunload guard is nonetheless ARMED, and that is the second thing this case pins. A
  // freshly created document has never been saved, so the app already calls it dirty — meaning
  // "dirty" and "a write is pending" are different facts, and a green that keys the record on the
  // dirty flag (the nearest thing to hand) would log here. It must key on pending work instead.
  //
  // RED 2026-07-29: passes already — it is the escape guard for the case above, and lands skipped
  // with its twin so the pair is un-skipped together by the green.
  it.skip('records nothing when the editor unmounts with no edit pending at all', async () => {
    const { unmount } = await renderCreatedDocument()

    expect(documentApi.saveDocument).not.toHaveBeenCalled()
    // Nothing armed and nothing sent — the exact inverse of the case above, and the half of this
    // pair's discrimination the dirty flag on the next line cannot express.
    expect(vi.getTimerCount()).toBe(0)
    // ARMED anyway — a freshly created document has never been saved. This is the assertion that
    // makes a green keyed on the dirty flag fail here while still passing the settled-write twin.
    expect(dispatchBeforeUnload()).toBe(true)

    unmount()

    expectNoAbandonmentRecorded()
  })
})
