import { StrictMode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { DocumentEditorPage } from '../DocumentEditorPage'
import { loadEditorDocument } from '../../api/editorDocumentApi'
import { loadEditQuota, type EditQuotaState } from '../../api/editQuotaApi'

// Story 19, Frontend Scenario 1.1 — "The editor and chat panel render side by side with an empty
// history" (`tests/02_UI_Tests.md`).
//
//   Given the user opens a document that has never been edited by AI
//   Then the document content is shown in the editor
//   And the chat panel is shown with its empty state
//   And the message input is enabled
//
// Every testid and the empty-state sentence are copied from
// `acceptance/statements/frontend/ai_chat/empty_chat_panel_statements.py`. If the two lists ever
// disagree, the layers specify two different UIs and one of them passes against a screen no user
// sees.
//
// WHAT THIS FILE DOES NOT COVER, ON PURPOSE. The document here is pristine, so nothing in it can
// tell a conditional empty state from an unconditional one — that half lives in
// `AiChatPanel.history.test.tsx`, which renders a NON-empty history. And the quota read is
// resolved here; the failed read is `DocumentEditorPage.quotaReadFailed.test.tsx`.
//
// The third Then — "the message input is enabled" — has NO case of its own here, and that is an
// existence check, not an omission: `DocumentEditorPage.overQuota.test.tsx:173` already asserts
// exactly that, through this same page, for a within-quota account. Re-typing it would be a second
// copy that can only ever fail alongside the first. What 1.1 genuinely adds on that line is the
// failed-read guard, which is the sibling file above.

const MANUAL_EDITOR = 'manual-editor'
const AI_CHAT_PANEL = 'ai-chat-panel'
const MESSAGE_LIST = 'ai-chat-message-list'
const EMPTY_STATE = 'ai-chat-empty-state'

// Prefix, and scoped INSIDE the list, for the reason scenario 0.1 established: an exact testid
// that exists nowhere makes an absence check vacuous forever. Matching the whole `ai-chat-message`
// namespace means no naming choice in scenario 1.2 (which renders the first real rows) can slip
// past it. The list scope is what keeps the composer's own `ai-chat-message-input` from matching.
const ANY_MESSAGE = '[data-testid^="ai-chat-message"]'

const EXPECTED_EMPTY_STATE_TEXT =
  'Документ готов. Напишите, что нужно изменить — я поправлю текст и сохраню новую версию.'

const DOCUMENT_ID = '3f1c6a20-9d4e-4b71-a0c8-5e2b7d84f193'
const DOCUMENT_PARAGRAPH_TEXT = 'Введение к докладу о квантовых вычислениях'
const DOCUMENT = {
  documentId: DOCUMENT_ID,
  content: `<p>${DOCUMENT_PARAGRAPH_TEXT}</p>`,
  version: 1,
}

// Typed, not an inline literal: the union in `editQuotaApi.ts` is the contract this page agrees
// with, and a structural copy would keep type-checking against a module it no longer matches.
const WITHIN_QUOTA: EditQuotaState = { exhausted: false, resetsAt: null }

vi.mock('../../api/editorDocumentApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/editorDocumentApi')>()
  return { ...actual, loadEditorDocument: vi.fn() }
})
vi.mock('../../api/editQuotaApi', () => ({ loadEditQuota: vi.fn() }))

const loadEditorDocumentMock = vi.mocked(loadEditorDocument)
const loadEditQuotaMock = vi.mocked(loadEditQuota)

// StrictMode — the wrapper `main.tsx` puts around `App` — so the call-count assertions below mean
// something: a naive `useEffect` fetch passes an unwrapped once-per-render assertion and
// double-fires in dev.
function renderPristineEditor() {
  loadEditorDocumentMock.mockResolvedValue(DOCUMENT)
  loadEditQuotaMock.mockResolvedValue(WITHIN_QUOTA)
  return render(
    <StrictMode>
      <MemoryRouter initialEntries={[`/documents/${DOCUMENT_ID}`]}>
        <Routes>
          <Route path="/documents/:documentId" element={<DocumentEditorPage />} />
        </Routes>
      </MemoryRouter>
    </StrictMode>,
  )
}

// An unpinned count passes a page that re-reads on every render — a request per keystroke, once
// this panel's composer is live. 0.1's and 0.2's lesson, restated where it can still fail.
function expectBothLoadsIssuedExactlyOnce() {
  expect(loadEditorDocumentMock).toHaveBeenCalledExactlyOnceWith(DOCUMENT_ID)
  expect(loadEditQuotaMock).toHaveBeenCalledExactlyOnceWith()
}

// Awaited first in every case: nothing may pass vacuously against a route still loading, and a
// same-named element in the page chrome cannot stand in for the chat panel's own.
async function chatPanel() {
  return await screen.findByTestId(AI_CHAT_PANEL)
}

// RED: neither `ai-chat-message-list` nor `ai-chat-empty-state` exists anywhere under
// `frontend/src` — `AiChatPanel` renders a heading, the revisions control and (while the quota is
// unknown) a notice, and has no history region at all.
describe.skip('DocumentEditorPage — a document never edited by AI', () => {
  beforeEach(() => {
    loadEditorDocumentMock.mockReset()
    loadEditQuotaMock.mockReset()
  })

  it('shows the stored document beside a chat panel in its empty state', async () => {
    renderPristineEditor()

    const panel = await chatPanel()

    // "Side by side" is only half true if the panel arrives beside a blank page. Equality on the
    // rendered text, not a substring: the content travels through Tiptap's schema, and a
    // substring check would pass on markup the schema mangled into a superset.
    const editor = await screen.findByTestId(MANUAL_EDITOR)
    expect(editor.textContent?.trim()).toBe(DOCUMENT_PARAGRAPH_TEXT)

    // The list is asserted ALONGSIDE the empty state, not instead of it: an empty state shown
    // while no history region exists satisfies "empty" by having nowhere to put messages, and
    // scenario 1.2 would then build the region from scratch on a panel this scenario called done.
    const list = await within(panel).findByTestId(MESSAGE_LIST)
    expect(list).toBeVisible()
    expect(list.querySelectorAll(ANY_MESSAGE)).toHaveLength(0)

    const emptyState = within(panel).getByTestId(EMPTY_STATE)
    // Visible, not merely mounted — the Selenium layer asserts `is_displayed()` and an empty state
    // behind `display:none` tells the user nothing about why the panel looks blank.
    expect(emptyState).toBeVisible()
    expect(emptyState.textContent?.trim()).toBe(EXPECTED_EMPTY_STATE_TEXT)

    expectBothLoadsIssuedExactlyOnce()
  })
})
