import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import * as documentApi from '../../api/documentApi'
import { clearSession, saveSession } from '../../../auth/utils/authSession'
import {
  crossDebounceBoundary,
  editorContentHtml,
  typeAndFireAutosave,
  typeIntoEditor,
  useAutosaveFailureFakeTimers,
} from './ManualEditor.autosave.testSupport'
import { CREATED_VERSION, renderCreatedDocument } from './ManualEditor.autosaveRender.testSupport'
import {
  EDITED_CONTENT,
  EDITED_PLAIN,
  REVISED_CONTENT,
  REVISED_PLAIN,
  SAVED_CONTENT,
  SAVED_PLAIN,
  SAVED_VERSION,
  playOutRetrySchedule,
} from './ManualEditor.autosaveFixture'
import {
  SAVED_BADGE_CLASS,
  SAVED_STATUS,
  SAVE_ERROR_TESTID,
  dispatchBeforeUnload,
} from './ManualEditor.saveStatus.testSupport'
import {
  ACCESS_TOKEN,
  DIVERGED_VERSION,
  FINAL_VERSION,
  REFRESH_TOKEN,
  REPAIRED_VERSION,
  RE_SAVED_VERSION,
  expectGet,
  expectPut,
  failure,
  ok,
  scriptFetch,
} from './ManualEditor.autosaveRevertRepairsDivergence.testSupport'

// Only `createDocument` is stubbed. Everything below it — `saveDocument`, `send`, `authorizedRequest`,
// `httpClient` — runs for real against a scripted `fetch`.
vi.mock('../../api/documentApi', async (importOriginal) => ({
  ...(await importOriginal<typeof documentApi>()),
  createDocument: vi.fn(),
}))

// Scenario H9.4 — the case the whole memory fix exists for, end to end.
//
// Its two halves are each pinned, and NOTHING pinned their composition. The component half
// (ManualEditor.autosaveDirtyGuardServerErrorRevert / TimeoutRevert) proves the retry issues a REAL
// PUT after a 5xx that may have landed; but its third call always succeeds, so it stops at "a write
// went out" and never reaches the branch that motivates nulling the memory: the 504'd write DID
// commit, the server is a version ahead, and the revert's PUT is therefore STALE. The api half
// (documentApi.conflict.test.ts) proves `saveDocument` answers a 409 with refetch-and-retry — in
// isolation, with no editor above it. So the actual user-visible claim, "the divergence is
// repaired", was the property neither suite made: break the composition on either side and both
// stay green.
//
// The mock boundary is what made that possible. Every suite in the autosave family carries
// `vi.mock('../../api/documentApi')`, which stubs out the exact module holding the repair. This one
// mocks `fetch` instead, so the repair has to actually happen for the assertions to pass.
describe('ManualEditor — a revert whose PUT is stale is repaired, not lost (H9.4)', () => {
  useAutosaveFailureFakeTimers()

  beforeEach(() => {
    saveSession({ accessToken: ACCESS_TOKEN, refreshToken: REFRESH_TOKEN })
  })

  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
  })

  it('refetches and re-PUTs the reverted content when the 504 turns out to have landed', async () => {
    const fetchMock = scriptFetch([
      // 1. the baseline save the server confirms — the guard now remembers SAVED_CONTENT.
      () => ok(SAVED_CONTENT, SAVED_VERSION),
      // 2. the edit's PUT: the proxy answers 504 while the origin COMMITS it. Everything after this
      //    line is the server being a version ahead of what the client believes.
      () => failure(504),
      // 3. the retry carrying the reverted content, at the version the client still holds — stale
      //    now, so the lost-update guard fires exactly as it must.
      () => failure(409, { error_code: 'VERSION_CONFLICT' }),
      // 4. saveDocument's own recovery: refetch. The GET is what reveals the divergence — the server
      //    holds the EDITED text the user has already undone.
      () => ok(EDITED_CONTENT, DIVERGED_VERSION),
      // 5. and the repair: the same reverted content, re-PUT at the version just fetched.
      () => ok(SAVED_CONTENT, REPAIRED_VERSION),
      // 6. a later edit, proving the repaired version was adopted rather than dropped.
      () => ok(REVISED_CONTENT, RE_SAVED_VERSION),
      // 7. and one more, so the version THAT save returned is observed being carried too — the
      //    chain is only proven unbroken at the hop that reads it back.
      () => ok(EDITED_CONTENT, FINAL_VERSION),
    ])

    await renderCreatedDocument()

    await typeAndFireAutosave(SAVED_PLAIN)
    expectPut(fetchMock, 1, SAVED_CONTENT, CREATED_VERSION)
    expect(screen.getByText(SAVED_STATUS)).toHaveClass(SAVED_BADGE_CLASS)

    await typeAndFireAutosave(EDITED_PLAIN)
    expectPut(fetchMock, 2, EDITED_CONTENT, SAVED_VERSION)
    // Transient: no banner, a backoff pending, the cycle still in flight.
    expect(screen.queryByTestId(SAVE_ERROR_TESTID)).toBeNull()

    // The undo lands INSIDE the backoff window, so it can only queue.
    await typeIntoEditor(SAVED_PLAIN)
    expect(dispatchBeforeUnload()).toBe(true)

    await playOutRetrySchedule()

    // The retry goes out stale — and is repaired rather than surfacing. A composition that broke
    // (the component swallowing the conflict, or saveDocument dropping its refetch) leaves the
    // server holding EDITED_CONTENT while the editor shows the revert: the silent divergence.
    expectPut(fetchMock, 3, SAVED_CONTENT, SAVED_VERSION)
    expectGet(fetchMock, 4)
    expectPut(fetchMock, 5, SAVED_CONTENT, DIVERGED_VERSION)
    expect(fetchMock).toHaveBeenCalledTimes(5)

    // The user-visible half of "repaired", and the one nothing else here can stand in for: the GET
    // at call 4 handed back EDITED_CONTENT — the text the user has already undone. A green that
    // adopts the REFETCHED body into the editor silently un-does the undo, and every request, badge
    // and guard assertion in this test still passes while the screen shows the wrong paragraph.
    expect(editorContentHtml()).toBe(SAVED_CONTENT)
    expect(screen.getByText(SAVED_STATUS)).toHaveClass(SAVED_BADGE_CLASS)
    expect(screen.queryByTestId(SAVE_ERROR_TESTID)).toBeNull()
    expect(dispatchBeforeUnload()).toBe(false)

    // The REPAIRED version — not the stale one the retry sent — is what the next write carries. A
    // green that repairs the content but leaves the client's version behind earns a 409 on every
    // subsequent save, and every assertion above still passes.
    await typeIntoEditor(REVISED_PLAIN)
    expect(dispatchBeforeUnload()).toBe(true)
    await crossDebounceBoundary()
    expectPut(fetchMock, 6, REVISED_CONTENT, REPAIRED_VERSION)
    // Exactly one write for that edit. Without the count a second PUT chained off the resolve
    // handler is invisible: the extra call only makes `scriptFetch` reject, which the save cycle
    // treats as a transport failure and the suite's silenced console hides.
    expect(fetchMock).toHaveBeenCalledTimes(6)
    expect(editorContentHtml()).toBe(REVISED_CONTENT)
    expect(screen.getByText(SAVED_STATUS)).toHaveClass(SAVED_BADGE_CLASS)
    expect(dispatchBeforeUnload()).toBe(false)

    // One more hop, because a version is only proven adopted at the write that CARRIES it: call 6
    // returned RE_SAVED_VERSION, and nothing above reads it back. Without this the repair could
    // leave the client one version behind from here on and the whole test stays green.
    await typeIntoEditor(EDITED_PLAIN)
    await crossDebounceBoundary()
    expectPut(fetchMock, 7, EDITED_CONTENT, RE_SAVED_VERSION)
    expect(fetchMock).toHaveBeenCalledTimes(7)
    expect(editorContentHtml()).toBe(EDITED_CONTENT)
    expect(dispatchBeforeUnload()).toBe(false)
  })
})
