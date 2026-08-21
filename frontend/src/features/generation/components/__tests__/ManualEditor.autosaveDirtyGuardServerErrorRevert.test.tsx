import { describe, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import type { HttpError } from '../../../../shared/api/httpClient'
import { isTransientFailure } from '../../utils/autosaveRetryPolicy'
import * as documentApi from '../../api/documentApi'
import { typeIntoEditor, useAutosaveFailureFakeTimers } from './ManualEditor.autosave.testSupport'
import {
  CREATED_DOCUMENT_ID,
  renderCreatedDocument,
} from './ManualEditor.autosaveRender.testSupport'
import {
  SAVED_CONTENT,
  SAVED_PLAIN,
  SAVED_VERSION,
  echoSavedAtRetryVersion,
  playOutRetrySchedule,
  saveBaselineThenTransientFailure,
} from './ManualEditor.autosaveFixture'
import {
  SAVED_BADGE_CLASS,
  SAVED_STATUS,
  SAVE_ERROR_TESTID,
  dispatchBeforeUnload,
} from './ManualEditor.saveStatus.testSupport'

vi.mock('../../api/documentApi')

// Scenario H9.4 — the same "the server's content is UNKNOWN" property as the timeout sibling
// (ManualEditor.autosaveDirtyGuardTimeoutRevert.test.tsx), arriving as a STATUS CODE instead of a
// client-side deadline. `isTransientFailure`'s `status >= 500` puts these on the retry side, which is
// right; what it cannot say is whether the write landed, and that is the question the guard's memory
// turns on. Both of these are servers that had the request in hand when they failed.
//
// This suite exists because the predicate's CALL SITE, not its shape, is what ships: a green that
// exports a perfectly correct `mayHaveLandedServerSide` and never calls it — or calls it only for
// `RequestTimeoutError` — passes every unit case, both older component suites, and tsc, while a 504
// still takes the suppression branch. Removing or narrowing the wiring in useDocumentSave's catch
// branch must fail HERE.
//
// The inverse (a 503, which answers that it did NOT take the write, and where suppression is
// correct) stays pinned in ManualEditor.autosaveDirtyGuardBackoffRevert.test.tsx.
const GATEWAY_TIMEOUT: HttpError = { status: 504, body: {} }
// The only 5xx this system actually emits: exception_handlers.py's catch-all returns 500, and
// nothing in front of the origin emits anything else. So this is not an exotic case — it is THE
// production shape of a failed autosave, and it had no component-level coverage at all.
const ORIGIN_SERVER_ERROR: HttpError = { status: 500, body: {} }

// The shared body of both cases: baseline save the server confirms, an edit that fails with
// `rejection`, an undo back to the saved content inside the backoff window, then the schedule played
// out. The revert must go out as a REAL write — anything the failed PUT may have committed is
// overwritten by the content the user can actually see.
async function expectRevertIsWrittenAfter(rejection: HttpError) {
  // The scenario presupposes the failure is retried at all rather than surfacing a banner outright.
  expect(isTransientFailure(rejection)).toBe(true)

  await renderCreatedDocument()

  vi.mocked(documentApi.saveDocument)
    .mockResolvedValueOnce({ status: 'saved', version: SAVED_VERSION, content: SAVED_CONTENT })
    .mockRejectedValueOnce(rejection)
    .mockImplementation(echoSavedAtRetryVersion)

  await saveBaselineThenTransientFailure()

  // The undo lands INSIDE the backoff window, so it can only queue.
  await typeIntoEditor(SAVED_PLAIN)
  expect(dispatchBeforeUnload()).toBe(true)

  await playOutRetrySchedule()

  expect(documentApi.saveDocument).toHaveBeenCalledTimes(3)
  expect(documentApi.saveDocument).toHaveBeenNthCalledWith(
    3,
    CREATED_DOCUMENT_ID,
    SAVED_CONTENT,
    SAVED_VERSION,
  )
  // And it converges: one real write settles the document, it does not chain a fourth.
  expect(screen.getByText(SAVED_STATUS)).toHaveClass(SAVED_BADGE_CLASS)
  expect(screen.queryByTestId(SAVE_ERROR_TESTID)).toBeNull()
  expect(dispatchBeforeUnload()).toBe(false)
}

describe('ManualEditor — a revert after a 5xx that may have landed is still written (H9.4)', () => {
  useAutosaveFailureFakeTimers()

  it('retries with the reverted content after a 504 — the proxy gave up on an origin mid-write', async () => {
    await expectRevertIsWrittenAfter(GATEWAY_TIMEOUT)
  })

  it('retries with the reverted content after a 500 — the failure may be post-commit', async () => {
    await expectRevertIsWrittenAfter(ORIGIN_SERVER_ERROR)
  })
})
