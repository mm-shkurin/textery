import { describe, expect, it, vi } from 'vitest'
import { act, screen } from '@testing-library/react'
import * as documentApi from '../../api/documentApi'
import {
  defer,
  editorContentHtml,
  flushMicrotasks,
  typeAndFireAutosave,
  useAutosaveFakeTimers,
} from './ManualEditor.autosave.testSupport'
import {
  CREATED_DOCUMENT_ID,
  CREATED_VERSION,
  renderCreatedDocument,
} from './ManualEditor.autosaveRender.testSupport'
import { RETRY_VERSION, SAVED_VERSION, asParagraph } from './ManualEditor.autosaveFixture'
import {
  DIRTY_STATUS,
  SAVED_BADGE_CLASS,
  SAVED_STATUS,
  dispatchBeforeUnload,
} from './ManualEditor.saveStatus.testSupport'

vi.mock('../../api/documentApi')

// Vocabulary local to this suite: the shared fixture names a baseline-edit-revision story, whereas
// this one needs an ordered first/second pair plus a body the server never legitimately holds.
// Derived through asParagraph so the text typed and the HTML asserted on the wire cannot drift.
const FIRST_PLAIN = 'first version'
const SECOND_PLAIN = 'second version'
const FIRST_CONTENT = asParagraph(FIRST_PLAIN)
const SECOND_CONTENT = asParagraph(SECOND_PLAIN)
// Deliberately unlike anything the user typed: if the stale response were ever adopted, the editor
// assertions below name exactly which response clobbered it rather than failing on a near-miss.
const STALE_SERVER_CONTENT = asParagraph('STALE SERVER')

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

describe('ManualEditor — out-of-order autosaves reflect the latest edit and content (E3.3/H9.2)', () => {
  // Timers only — this suite deliberately does NOT silence console.error: nothing here rejects, so a
  // console.error appearing would be a real diagnostic worth seeing rather than expected noise.
  useAutosaveFakeTimers()

  it('keeps the latest edit and status when a queued save resolves after a stale first save, and the stale response never clobbers the newer content', async () => {
    await renderCreatedDocument()

    // The first save (A) is held pending so a second edit lands while A is still "in flight".
    const saveA = defer()
    const saveB = defer()
    vi.mocked(documentApi.saveDocument)
      .mockReturnValueOnce(saveA.promise)
      .mockReturnValueOnce(saveB.promise)

    // Edit #1 → debounce → first autosave (A) fires and stays pending.
    await typeAndFireAutosave(FIRST_PLAIN)
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(
      1,
      CREATED_DOCUMENT_ID,
      FIRST_CONTENT,
      CREATED_VERSION,
    )

    // Edit #2 lands while A is still in flight: it must queue a re-save, NOT launch a second
    // concurrent saveDocument. Advancing the debounce here re-enters save() which finds A in
    // flight and only sets the "save again" flag.
    await typeAndFireAutosave(SECOND_PLAIN)
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)
    // Unsent keystrokes exist, so the leave-guard is armed. Asserted here so the `false` at the end
    // of the test means "the guard stood down", not "no guard was ever installed" — ManualEditor
    // registers the beforeunload listener only while dirty.
    expect(dispatchBeforeUnload()).toBe(true)

    // A resolves LAST-in-wall-clock but FIRST-in-order, carrying stale server content that differs
    // from what the editor now holds. The resolve handler must NOT adopt it (editor moved on), and
    // must fire the queued save (B) with the LATEST content and A's returned version.
    await act(async () => {
      saveA.resolve({ status: 'saved', version: SAVED_VERSION, content: STALE_SERVER_CONTENT })
    })
    await flushMicrotasks()
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(2)
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(
      2,
      CREATED_DOCUMENT_ID,
      SECOND_CONTENT,
      SAVED_VERSION,
    )
    // The stale A response did not overwrite the editor's newer content.
    expect(editorContentHtml()).toBe(SECOND_CONTENT)

    // B — the save for the latest edit — resolves and settles the shown state.
    await act(async () => {
      saveB.resolve({ status: 'saved', version: RETRY_VERSION, content: SECOND_CONTENT })
    })
    await flushMicrotasks()

    // Final state reflects the latest edit (B): content preserved, status is exactly "saved".
    expect(editorContentHtml()).toBe(SECOND_CONTENT)
    // B settled the cycle — it must not chain a third write off its own resolve handler.
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(2)
    // Strict status: the saved badge is the branch that rendered (asserted by its variant class —
    // re-reading the text getByText already matched on could never fail), and the dirty status must
    // be gone. A stale-A clobber reverting to dirty fails on both.
    expect(screen.getByText(SAVED_STATUS)).toHaveClass(SAVED_BADGE_CLASS)
    expect(screen.queryByText(DIRTY_STATUS)).toBeNull()
    // ...and the document is clean all the way through to the leave-guard, not merely in the badge.
    expect(dispatchBeforeUnload()).toBe(false)
  })
})
