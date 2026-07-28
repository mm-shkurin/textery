import { describe, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import { CONFLICT_ERROR_MESSAGE, SAVE_ERROR_MESSAGE } from '../../hooks/useDocumentSave'
import { VersionConflictError } from '../../../../shared/api/send'
import * as documentApi from '../../api/documentApi'
import {
  CREATED_DOCUMENT_ID,
  CREATED_VERSION,
  crossDebounceBoundary,
  renderCreatedDocument,
  typeIntoEditor,
  useAutosaveFailureFakeTimers,
} from './ManualEditor.autosave.testSupport'
import {
  EDITED_CONTENT,
  EDITED_PLAIN,
  SAVED_CONTENT,
  SAVED_PLAIN,
  SAVED_VERSION,
} from './ManualEditor.autosaveFixture'
import {
  DIRTY_BADGE_CLASS,
  DIRTY_STATUS,
  SAVED_BADGE_CLASS,
  SAVED_STATUS,
  SAVE_ERROR_TESTID,
  dispatchBeforeUnload,
} from './ManualEditor.saveStatus.testSupport'

vi.mock('../../api/documentApi')

// Scenario H9.4, pre-condition (f) — what the dirty guard is allowed to remember AFTER a save has
// failed terminally.
//
// The guard settling the clean state on the suppression path (the regression fix) is right only
// while nothing has contradicted the remembered content. A terminal failure contradicts it: the
// banner is up and the last thing the user knows about this document is that a write to it did NOT
// land. Reverting back to the remembered content and crossing a debounce boundary would then hit
// the guard, suppress the write, and settle clean — flipping the badge to «Сохранено» and tearing
// down the beforeunload listener directly above a banner reading «…не сохранён». The conflict case
// makes it worse than cosmetic: saveDocument answers the FIRST 409 itself with a refetch and a
// last-writer-wins retry, so a VersionConflictError reaching the hook means the SECOND PUT also
// conflicted — the server provably no longer holds what the guard remembers.
//
// So a terminal failure invalidates the memory outright: the guard suppresses only over content it
// has positively watched the server confirm and nothing has since called into question. The boundary
// after the revert therefore makes a REAL attempt — which is also the recovery the user wants, since
// a successful one clears the banner. Both tests reject that attempt too, so the assertions are
// about the failed state staying honest, not about the recovery succeeding.
describe('ManualEditor — a terminal save failure invalidates the dirty guard (H9.4 f)', () => {
  useAutosaveFailureFakeTimers()

  async function saveThenFail() {
    await renderCreatedDocument()
    await typeIntoEditor(SAVED_PLAIN)
    await crossDebounceBoundary()
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)
    // The baseline's own tuple, not just its count: this is the write whose success is what the
    // guard goes on to remember, so a wrong content or version here voids the whole premise.
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(
      1,
      CREATED_DOCUMENT_ID,
      SAVED_CONTENT,
      CREATED_VERSION,
    )
    expect(screen.getByText(SAVED_STATUS)).toHaveClass(SAVED_BADGE_CLASS)

    // The failing save. A fresh edit so the boundary has something to write.
    await typeIntoEditor(EDITED_PLAIN)
    await crossDebounceBoundary()
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(2)
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(
      2,
      CREATED_DOCUMENT_ID,
      EDITED_CONTENT,
      SAVED_VERSION,
    )
  }

  // Undoes the failed edit, restoring the exact bytes the guard remembers, and crosses the boundary.
  async function revertAndCrossBoundary() {
    await typeIntoEditor(SAVED_PLAIN)
    // Non-vacuity gate for nothing here — the assertions below are all positive — but it pins that
    // the revert really did re-dirty the document, so the boundary that follows is a live one.
    expect(dispatchBeforeUnload()).toBe(true)
    await crossDebounceBoundary()
  }

  function expectStillFailed(bannerMessage: string) {
    // A real write was attempted: the guard did NOT suppress over a memory a failure had voided.
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(3)
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(
      3,
      CREATED_DOCUMENT_ID,
      SAVED_CONTENT,
      SAVED_VERSION,
    )
    // …and since that attempt failed too, the document must not claim to be clean anywhere.
    // Exact text, not a substring: the banner's whole content is the message (its icon renders no
    // text), so toHaveTextContent would also pass for a message that merely embedded the expected
    // one — and the two failure kinds this suite distinguishes differ only in that wording.
    expect(screen.getByTestId(SAVE_ERROR_TESTID).textContent).toBe(bannerMessage)
    expect(screen.getByText(DIRTY_STATUS)).toHaveClass(DIRTY_BADGE_CLASS)
    expect(screen.queryByText(SAVED_STATUS)).toBeNull()
    expect(dispatchBeforeUnload()).toBe(true)
  }

  it('re-attempts the write after a generic failure instead of suppressing it as already saved', async () => {
    vi.mocked(documentApi.saveDocument)
      .mockResolvedValueOnce({ status: 'saved', version: SAVED_VERSION, content: SAVED_CONTENT })
      .mockRejectedValue(new Error('network down'))

    await saveThenFail()
    expect(screen.getByTestId(SAVE_ERROR_TESTID).textContent).toBe(SAVE_ERROR_MESSAGE)

    await revertAndCrossBoundary()
    expectStillFailed(SAVE_ERROR_MESSAGE)
  })

  it('re-attempts the write after a conflict that survived the refetch-and-retry', async () => {
    vi.mocked(documentApi.saveDocument)
      .mockResolvedValueOnce({ status: 'saved', version: SAVED_VERSION, content: SAVED_CONTENT })
      // saveDocument already answered one 409 with a refetch + retry; this is the second conflict,
      // i.e. the server is holding somebody else's write over the content the guard remembers.
      .mockRejectedValue(new VersionConflictError())

    await saveThenFail()
    expect(screen.getByTestId(SAVE_ERROR_TESTID).textContent).toBe(CONFLICT_ERROR_MESSAGE)

    await revertAndCrossBoundary()
    expectStillFailed(CONFLICT_ERROR_MESSAGE)
  })
})
