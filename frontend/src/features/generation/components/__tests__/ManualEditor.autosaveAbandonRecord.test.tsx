import { describe, expect, it, vi } from 'vitest'
import {
  renderCreatedDocument,
  renderFailedInitDocument,
  typeAndFireAutosave,
  typeIntoEditor,
  useAutosaveFailureFakeTimers,
} from './ManualEditor.autosave.testSupport'
import {
  SAVED_PLAIN,
  armServerConfirmsSavedContent,
  armServerRefusesWithProductionError,
  expectBaselineSaveOnWire,
} from './ManualEditor.autosaveFixture'
import {
  armServerNeverSettles,
  discardAttemptDiagnostics,
  expectAbandonmentRecorded,
  expectManualSaveCannotReachTheWire,
  expectNoAbandonmentRecorded,
  expectNoSaveOnWire,
  expectUnsentEditHeldInEditor,
} from './ManualEditor.autosaveAbandonFixture'
import { dispatchBeforeUnload, expectOnlySavedBadge } from './ManualEditor.saveStatus.testSupport'

vi.mock('../../api/documentApi')

// What this file must and must not say, and the CONSTRAINT ON THE GREEN that its two opposite
// directions create, are documented at the head of ./ManualEditor.autosaveAbandonFixture.ts —
// the module both this suite and its negative twin share. Read it before making either green:
// clearing hasPendingEditRef at the wrong early return trades a false record for total silent loss.

describe('ManualEditor — what the abandonment record must and must not say (H9.4 guards)', () => {
  useAutosaveFailureFakeTimers()

  it('records the abandonment when the editor unmounts with a request still in flight', async () => {
    const { unmount } = await renderCreatedDocument()
    // Never settles: the unmount lands INSIDE a request, not inside a backoff gap. No timer object
    // exists at this moment, and the write is nonetheless gone the instant the component dies.
    armServerNeverSettles()

    await typeAndFireAutosave(SAVED_PLAIN)
    // The in-flight request is the USER's edit at the document's current version, not merely some
    // write — the OCC triple, not a bare count. What is abandoned has to be identifiable.
    expectBaselineSaveOnWire()
    // Provably unpersisted at the moment we walk away — the app's own guard is armed.
    expect(dispatchBeforeUnload()).toBe(true)

    unmount()

    expectAbandonmentRecorded()
  })

  it('records nothing when the editor unmounts with every write settled', async () => {
    const { unmount } = await renderCreatedDocument()
    armServerConfirmsSavedContent()
    // The non-vacuity gate for the stand-down below, observed in THIS case rather than borrowed from a
    // sibling: ManualEditor registers the beforeunload listener only while hasUnsavedChanges is true,
    // so a regression that never arms it satisfies every toBe(false) here. A freshly created document
    // has never been saved, so this is a provably-dirty moment.
    expect(dispatchBeforeUnload()).toBe(true)

    await typeAndFireAutosave(SAVED_PLAIN)
    // Settled means SETTLED: the write reached the wire as the user's edit, and the app says the
    // document is clean in its own voice. Without the badge, a green that clears hasUnsavedChanges
    // without the save ever resolving satisfies the `false` below and this case stops being the
    // "every write settled" twin at all.
    expectBaselineSaveOnWire()
    expectOnlySavedBadge()
    // Nothing is pending: the document is clean, so the browser guard has stood down. The armed
    // `true` this stand-down is measured against is asserted by the two cases below, which observe
    // it on the same fixture with work outstanding.
    expect(dispatchBeforeUnload()).toBe(false)

    unmount()

    // The negative twin. console.error is the whole of this app's diagnostics; a record written on
    // every ordinary in-app back-out is how the one that matters becomes invisible.
    expectNoAbandonmentRecorded()
  })

  it('records the abandonment once, not once per failed attempt already logged', async () => {
    const { unmount } = await renderCreatedDocument()
    armServerRefusesWithProductionError()

    await typeAndFireAutosave(SAVED_PLAIN)
    // The attempt that rejected was the user's edit at the document's current version — the premise
    // this case's "once, not once per attempt" claim is about.
    expectBaselineSaveOnWire()
    // Attempt 1's own rejection diagnostic belongs to the attempt, not to the abandonment.
    discardAttemptDiagnostics()

    unmount()

    expectAbandonmentRecorded()
  })

  // The THIRD window, and the only one an ordinary user reaches without a 5xx first: the debounce
  // gap. `useAbandonedSaveRecord` keys the record on isSavingRef, which a debounced edit has not set
  // yet — the save has been decided on but not started. useAutosave's own []-scoped cleanup drops
  // that timer in silence. ManualEditor.autosave.test.tsx:94 already proves the drop and asserts only
  // that no save fired; it does not spy console.error, so the silence is nobody's assertion.
  it('records the abandonment when the editor unmounts inside the debounce gap', async () => {
    const { unmount } = await renderCreatedDocument()

    // One edit, and the clock stays put — strictly inside AUTOSAVE_DEBOUNCE_MS. Nothing has been
    // sent, so isSavingRef was never set; the edit exists only as a pending timer.
    await typeIntoEditor(SAVED_PLAIN)
    expectNoSaveOnWire()
    // The edit is REAL and it is exactly the one this case names, and the app calls the document
    // unpersisted while holding it. Why each half is needed is at the helper.
    expectUnsentEditHeldInEditor()

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
  it('records nothing when the editor unmounts with no edit pending at all', async () => {
    const { unmount } = await renderCreatedDocument()

    expectNoSaveOnWire()
    // Nothing armed and nothing sent — the exact inverse of the case above, and the half of this
    // pair's discrimination the dirty flag on the next line cannot express.
    expect(vi.getTimerCount()).toBe(0)
    // ARMED anyway — a freshly created document has never been saved. This is the assertion that
    // makes a green keyed on the dirty flag fail here while still passing the settled-write twin.
    expect(dispatchBeforeUnload()).toBe(true)

    unmount()

    expectNoAbandonmentRecorded()
  })

  // The FOURTH window, and the only one with real, TOTAL loss — every case above walks away from one
  // unsent edit over a document the server already holds; this one walks away from the whole document.
  // `ManualEditor.tsx:35` starts `documentId` as null and the editor is mounted and typeable while init
  // is still in flight or after it FAILED, which the file states outright («with no documentId there is
  // nothing to save TO»). Forty minutes of typing can go in there.
  //
  // And it is the one window the current clear-site makes SILENT. The debounce fires, useAutosave nulls
  // its timer and clears hasPendingEditRef on the assumption `save()` takes over the window — then
  // `save()` returns at `useDocumentSave.ts:172` on `!documentId` without ever setting isSavingRef.
  // Flag false, isSavingRef false, no timer, and no re-arm until the next keystroke: at unmount the
  // record's key reads exactly like an untouched document. That is the inversion of what H9.4 exists
  // for, so it must land BEFORE the green that clears the flag wherever `save()` runs — that fix is
  // precisely the mutation that would re-open this hole with nothing opposing it.
  //
  // Not passable by logging in the cleanup unconditionally: ManualEditor.autosaveAbandonFalseRecord
  // and the untouched-document twin above both fail on that.
  //
  // RED: expected "error" to be called 1 times, but got 0 times — nothing is recorded. The debounce
  // fired and cleared hasPendingEditRef; save() bailed on !documentId without setting isSavingRef, so
  // the []-scoped cleanup sees neither key.
  // RED 2026-07-30, awaiting the H9.4 green that moves the clear site.
  it.skip('records the abandonment when the editor unmounts with a document init never created', async () => {
    const { unmount } = await renderFailedInitDocument()

    // Type, then let the deadline pass — the flag's ONLY clear site runs, and the save it hands off to
    // does nothing. Crossing the boundary is what makes this case different from the debounce-gap case
    // above, which stops one tick short of it.
    await typeAndFireAutosave(SAVED_PLAIN)
    // There was never anywhere to send it — and this case says "no POSSIBLE request", not merely "no
    // request yet". The manual Сохранить is the one remaining path into `save()`; clicking it with the
    // button provably live and watching the wire stay empty is `useDocumentSave.ts:172`'s
    // `if (!documentId) return` observed from outside the component.
    await expectManualSaveCannotReachTheWire()
    // The work is REAL and it is still only in the editor — the whole of what is about to be lost,
    // over a document that does not exist.
    expectUnsentEditHeldInEditor()

    unmount()

    expectAbandonmentRecorded()
  })
})
