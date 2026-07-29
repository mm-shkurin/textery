import { describe, expect, it, vi } from 'vitest'
import type { HttpError } from '../../../../shared/api/httpClient'
import * as documentApi from '../../api/documentApi'
import {
  CREATED_VERSION,
  defer,
  renderCreatedDocument,
  typeAndFireAutosave,
  useAutosaveFailureFakeTimers,
} from './ManualEditor.autosave.testSupport'
import { ABANDONED_SAVE_LOG, SAVED_PLAIN } from './ManualEditor.autosaveFixture'
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

const PRODUCTION_SERVER_ERROR: HttpError = { status: 500, body: {} }

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

    expect(console.error).toHaveBeenCalledTimes(1)
    expect(console.error).toHaveBeenCalledWith(ABANDONED_SAVE_LOG)
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
    expect(console.error).not.toHaveBeenCalled()
  })

  it('records the abandonment once, not once per failed attempt already logged', async () => {
    const { unmount } = await renderCreatedDocument()
    vi.mocked(documentApi.saveDocument).mockRejectedValue(PRODUCTION_SERVER_ERROR)

    await typeAndFireAutosave(SAVED_PLAIN)
    // Attempt 1's own rejection diagnostic belongs to the attempt, not to the abandonment.
    vi.mocked(console.error).mockClear()

    unmount()

    expect(console.error).toHaveBeenCalledTimes(1)
    expect(console.error).toHaveBeenCalledWith(ABANDONED_SAVE_LOG)
  })
})
