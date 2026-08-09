import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { DocumentEditorPage } from '../DocumentEditorPage'
import { DocumentNotFoundError, loadEditorDocument } from '../../api/editorDocumentApi'

// Story 19, Frontend Scenario 0.1 — "A document that cannot be loaded blocks the chat panel with
// a way out" (`tests/02_UI_Tests.md`).
//
// WHY THIS EXISTS ALONGSIDE THE SELENIUM TEST. The acceptance test
// (`acceptance/tests/frontend/ai_chat/test_document_not_found_acceptance.py`) only ever opens the
// route with a random UUID, so it can never tell a conditional blocker from an unconditional one:
// a component that renders the blocker on every load would pass it. That gap is a component-level
// obligation, and it is what the second case below pins — the SAME component, given a document
// that loads, must render the chat workspace and NO blocker.
//
// SEAM. Only `loadEditorDocument` is mocked; `DocumentNotFoundError` stays real so the test
// rejects with the type production code will actually match on. Mapping the 404 body onto that
// type is `red-frontend-api`'s scope, not this unit's.
//
// BOTH HALVES OF THE GIVEN — "absent or not the user's" — reach the client as the same 404
// (`endpoints.md`: "All seven endpoints share one 404 body"), hence the same DocumentNotFoundError
// and the same blocker. A second test case rejecting with the identical error for "another
// account's document" would assert nothing the first does not; the two halves are one branch here.
//
// DELIBERATELY NOT PINNED: the loading state that scenario 8.8 owns. Every assertion below is
// awaited, so an interim spinner render is permitted — this test neither requires nor forbids it.

const NOT_FOUND_BLOCKER = 'document-not-found'
const NOT_FOUND_TITLE = 'document-not-found-title'
const NOT_FOUND_DOCUMENTS_LINK = 'document-not-found-documents-link'

// The editor root. The success case REQUIRES this exact testid to render, which is what keeps the
// failure case's absence check honest: without a positive counterpart, green naming its root
// anything else (`document-editor`, `editor-root`) would leave the absence check passing while the
// editor sits on screen beside the blocker. This test is the specification — the root is named
// `manual-editor`, reusing the Story 5/18 editor testid, and green must match.
const MANUAL_EDITOR = 'manual-editor'

// Two locators for the chat panel, deliberately asymmetric.
//
// ABSENCE (failure case) uses the prefix: an exact-match absence check would stay vacuous no
// matter what scenario 1.1 names the panel, whereas the whole `ai-chat-*` namespace is
// un-slippable — no later naming choice can render a chat element past it.
//
// PRESENCE (success case) uses an exact testid, not the prefix: `not.toBeNull()` on a prefix
// selector is satisfied by any incidental `ai-chat-*` node — a wrapper div, a hidden placeholder.
// The panel is named here, now, and scenario 1.1 inherits the name.
const AI_CHAT_ANY = "[data-testid^='ai-chat']"
const AI_CHAT_PANEL = 'ai-chat-panel'

const DOCUMENTS_LIST_PATH = '/documents'
const EXPECTED_NOT_FOUND_TITLE = 'Документ не найден'
const EXPECTED_DOCUMENTS_LINK_TEXT = 'К моим документам'

const ABSENT_DOCUMENT_ID = '1f0b9c4e-8a2d-4f31-9b77-6c5e0a1d2b34'
const OWN_DOCUMENT_ID = '7a3d5e19-2c64-4b08-8f52-91ad3e7c0b6f'
const OWN_DOCUMENT = {
  documentId: OWN_DOCUMENT_ID,
  content: '<p>Введение к докладу</p>',
  version: 3,
}
// The one field of the loaded document this scenario can pin: its rendered text. Asserting it is
// what stops the success branch from being satisfiable by a component that renders an empty
// workspace and drops the resolved document on the floor.
//
// `version` is deliberately NOT asserted: no scenario in `02_UI_Tests.md` shows it to the user (it
// travels with edit submissions, scenarios 3.x), so pinning a display for it here would invent UI
// the spec does not define. `documentId` is pinned instead through the load call below.
const EXPECTED_DOCUMENT_TEXT = 'Введение к докладу'

vi.mock('../../api/editorDocumentApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/editorDocumentApi')>()
  return { ...actual, loadEditorDocument: vi.fn() }
})

const loadEditorDocumentMock = vi.mocked(loadEditorDocument)

function renderAtDocumentRoute(documentId: string) {
  return render(
    <MemoryRouter initialEntries={[`${DOCUMENTS_LIST_PATH}/${documentId}`]}>
      <Routes>
        <Route path="/documents/:documentId" element={<DocumentEditorPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

// RED 2026-08-09: DocumentEditorPage is a stub that renders null and loadEditorDocument is a stub
// that throws — neither branch exists. Both cases fail on the awaited element that never appears.
// Un-skip in green-frontend for Story 19, Frontend Scenario 0.1.
describe.skip('DocumentEditorPage — a document that cannot be loaded', () => {
  beforeEach(() => {
    loadEditorDocumentMock.mockReset()
  })

  it('blocks with a not-found panel and a way out instead of the editor and chat', async () => {
    loadEditorDocumentMock.mockRejectedValue(new DocumentNotFoundError())

    const { container } = renderAtDocumentRoute(ABSENT_DOCUMENT_ID)

    const blocker = await screen.findByTestId(NOT_FOUND_BLOCKER)
    expect(within(blocker).getByTestId(NOT_FOUND_TITLE).textContent).toBe(
      EXPECTED_NOT_FOUND_TITLE,
    )

    // Scoped INSIDE the blocker, and asserted on the same element the scope found. A documents
    // link elsewhere in the chrome would otherwise satisfy "a way out" the blocker never offers,
    // and a caption-only check would pass a <span> or an href="#".
    const wayOut = within(blocker).getByTestId(NOT_FOUND_DOCUMENTS_LINK)
    expect(wayOut.textContent).toBe(EXPECTED_DOCUMENTS_LINK_TEXT)
    // An anchor, asserted before the href: `toHaveAttribute('href', …)` alone would pass on a
    // <span href="/documents">, which is not a way out — it navigates nowhere when clicked.
    expect(wayOut.tagName).toBe('A')
    expect(wayOut).toHaveAttribute('href', DOCUMENTS_LIST_PATH)

    // Ordered after the blocker resolved, so these cannot pass vacuously against a tree that has
    // not rendered anything yet. `queryBy`/`querySelector`, not a visibility check: a
    // rendered-but-hidden editor is still the editor.
    expect(screen.queryByTestId(MANUAL_EDITOR)).toBeNull()
    expect(container.querySelector(AI_CHAT_ANY)).toBeNull()
    // Exactly once, with exactly that id: an unpinned call count passes a component that refetches
    // on every render, which is a live defect this branch would otherwise hide.
    expect(loadEditorDocumentMock).toHaveBeenCalledExactlyOnceWith(ABSENT_DOCUMENT_ID)
  })

  it('shows the editor with the loaded document and the chat panel, and no blocker', async () => {
    loadEditorDocumentMock.mockResolvedValue(OWN_DOCUMENT)

    renderAtDocumentRoute(OWN_DOCUMENT_ID)

    // Both halves of what the failure case asserts absent must be proved present here, by the SAME
    // testids — otherwise those absence checks pin nothing green is obliged to name.
    const editor = await screen.findByTestId(MANUAL_EDITOR)
    expect(within(editor).getByText(EXPECTED_DOCUMENT_TEXT)).toBeInTheDocument()
    expect(await screen.findByTestId(AI_CHAT_PANEL)).toBeInTheDocument()

    expect(screen.queryByTestId(NOT_FOUND_BLOCKER)).toBeNull()
    expect(loadEditorDocumentMock).toHaveBeenCalledExactlyOnceWith(OWN_DOCUMENT_ID)
  })
})
