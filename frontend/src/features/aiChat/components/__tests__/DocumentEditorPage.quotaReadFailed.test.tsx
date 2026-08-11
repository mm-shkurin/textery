import { StrictMode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { DocumentEditorPage } from '../DocumentEditorPage'
import { CHAT_PANEL_NOTICE } from '../AiChatPanel'
import { loadEditorDocument } from '../../api/editorDocumentApi'
import { loadEditQuota } from '../../api/editQuotaApi'

// Story 19, Frontend Scenario 1.1 — the guard its third Then invites a green phase to delete.
//
// THE REGRESSION THIS FORBIDS. "And the message input is enabled" has a cheap green: render the
// composer whenever the quota is not known to be exhausted. `AiChatPanel` withholds it while
// `quota === null`, and `useEditQuota` collapses a REJECTED read into that same `null` — so
// flipping that one branch satisfies the scenario and silently converts "we could not ask whether
// this account may edit" into "type away". The user then spends instructions that all bounce off
// a server-side 429. `DocumentEditorPage.overQuota.test.tsx` only ever `mockResolvedValue`s, so
// until this file the catch branch had no test observing the resulting UI at all.
//
// UN-SKIPPED, and that is deliberate (the `42ba5d94` precedent in this story): the guard already
// exists and is already correct, so there is no failing main to show. The RED evidence is
// MUTATION — see the work unit's report. Only a case that genuinely fails against main carries a
// skip.

const AI_CHAT_PANEL = 'ai-chat-panel'
const MESSAGE_INPUT = 'ai-chat-message-input'
const SEND_BUTTON = 'ai-chat-send-button'

const DOCUMENT_ID = '3f1c6a20-9d4e-4b71-a0c8-5e2b7d84f193'
const DOCUMENT = { documentId: DOCUMENT_ID, content: '<p>Введение</p>', version: 1 }

vi.mock('../../api/editorDocumentApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/editorDocumentApi')>()
  return { ...actual, loadEditorDocument: vi.fn() }
})
vi.mock('../../api/editQuotaApi', () => ({ loadEditQuota: vi.fn() }))

const loadEditorDocumentMock = vi.mocked(loadEditorDocument)
const loadEditQuotaMock = vi.mocked(loadEditQuota)

const QUOTA_READ_ERROR = 'quota endpoint unavailable'

// A REJECTED read and an IN-FLIGHT read render the same panel by design — `useEditQuota` collapses
// both to `null`, and the notice below is what the panel says in either case. So no DOM assertion
// can, on its own, tell this case apart from one where the rejection never fired: without the two
// guards this file installs, deleting the rejection entirely leaves every assertion green.
//
// The guards are what make the case about the FAILED read specifically:
//   1. `await expect(quotaRead).rejects` below — a settlement barrier. The DOM assertions cannot
//      run until the read has actually rejected, and a test that stopped firing the rejection
//      would hang here instead of quietly passing against the pending state.
//   2. this listener — the rejection must be HANDLED. `useEditQuota`'s `.catch` is the guard the
//      prose above credits; strip it and the rejection escapes the hook's `.then` chain onto a
//      derived promise nothing awaits. Our own `.rejects` handler sits on the base promise and
//      does not cover that chain, so the escape is still observable here.
const unhandledRejections: unknown[] = []
const recordUnhandledRejection = (reason: unknown) => {
  unhandledRejections.push(reason)
}

// Reached through `globalThis` with a local, minimal type rather than a bare `process`: this app
// has no `@types/node`, and adding one to make a test compile would be a build-config change
// riding in on a test review. Only the two methods used are declared.
type RejectionListener = (reason: unknown) => void
const { process: nodeProcess } = globalThis as unknown as {
  process: {
    on: (event: 'unhandledRejection', listener: RejectionListener) => void
    off: (event: 'unhandledRejection', listener: RejectionListener) => void
  }
}

// One macrotask: Node emits `unhandledRejection` at the end of the turn in which the promise went
// unhandled, so the assertion must not run in the same microtask checkpoint as the rejection.
async function flushRejectionBookkeeping() {
  await new Promise((resolve) => setTimeout(resolve, 0))
}

describe('DocumentEditorPage — the quota read failed', () => {
  beforeEach(() => {
    loadEditorDocumentMock.mockReset()
    loadEditQuotaMock.mockReset()
    unhandledRejections.length = 0
    nodeProcess.on('unhandledRejection', recordUnhandledRejection)
  })

  afterEach(() => {
    nodeProcess.off('unhandledRejection', recordUnhandledRejection)
  })

  it('withholds the composer rather than treating an unanswerable quota as permission', async () => {
    loadEditorDocumentMock.mockResolvedValue(DOCUMENT)
    // The rejection is held and fired by hand rather than handed over as `mockRejectedValue`.
    // An absence assertion against a promise that settled on its own schedule is unsynchronised:
    // it would pass on a page that had simply not rendered the composer YET. Firing it inside
    // `act` means the assertions below run strictly after React has processed the failure.
    let failTheQuotaRead!: (error: unknown) => void
    const quotaRead = new Promise<never>((_resolve, reject) => {
      failTheQuotaRead = reject
    })
    loadEditQuotaMock.mockReturnValue(quotaRead)

    render(
      <StrictMode>
        <MemoryRouter initialEntries={[`/documents/${DOCUMENT_ID}`]}>
          <Routes>
            <Route path="/documents/:documentId" element={<DocumentEditorPage />} />
          </Routes>
        </MemoryRouter>
      </StrictMode>,
    )

    const panel = await screen.findByTestId(AI_CHAT_PANEL)

    await act(async () => {
      failTheQuotaRead(new Error(QUOTA_READ_ERROR))
    })

    // The settlement barrier. Exact message, not `toThrow()` bare: a different failure reaching
    // this line would mean the page failed for something other than the quota read.
    await expect(quotaRead).rejects.toThrow(QUOTA_READ_ERROR)

    // Absent, not merely disabled — and absence, not invisibility. A composer rendered behind
    // `display:none` still submits whatever a script or an autofill puts in it, and a disabled one
    // is a different claim ("your quota is spent") from the true one ("we do not know").
    expect(within(panel).queryByTestId(MESSAGE_INPUT)).toBeNull()
    expect(within(panel).queryByTestId(SEND_BUTTON)).toBeNull()

    // The positive anchor. Without it this case is satisfied by a panel that failed to render at
    // all, or by one that quietly shows nothing where the composer should be — neither of which
    // tells the user why they cannot type.
    expect(within(panel).getByText(CHAT_PANEL_NOTICE)).toBeVisible()

    // Pinned, not merely "called": a page that re-reads the quota on every render would retry a
    // dead endpoint once per keystroke the moment this panel's composer goes live.
    expect(loadEditorDocumentMock).toHaveBeenCalledExactlyOnceWith(DOCUMENT_ID)
    expect(loadEditQuotaMock).toHaveBeenCalledExactlyOnceWith()

    // The failure was SWALLOWED by the hook, not left to escape. See the note above the listener.
    await flushRejectionBookkeeping()
    expect(unhandledRejections).toStrictEqual([])
  })
})
