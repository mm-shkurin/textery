import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import App from '../App'
import * as api from '../../features/generation/api/generationApi'
import * as documentApi from '../../features/generation/api/documentApi'
import { clearSession, saveSession } from '../../features/auth/utils/authSession'

// Story 18, scenario 2.1 — "When the text becomes ready, the surface becomes the editor, and the
// user made no extra click to get there".
//
// SEAM: the renderer/hook join, driven through the real UI with both api modules mocked — the
// established pattern of the two siblings in this directory. Chosen deliberately over the two
// alternatives this lane has been burned by before:
//
//   * renderHook on useGeneration / useFlowNavigation would pin hook STATE, which is not where the
//     defect is. `runPollAttempt` already sets state 'completed' today; what is missing is that
//     nothing turns that state into the editor, so a hook-level assertion could go green with the
//     surface still read-only — verbatim the "pins a contract one layer below where the defect
//     lives" mistake recorded against 1.1's red-frontend-api.
//   * generationApi / documentApi is red-frontend-api's seam and owns the from-generation wire
//     contract; it cannot see a surface at all.
//
// The transition is a RENDER decision spanning three files, and only a render can observe it:
// `useGeneration.runPollAttempt` handles `completed` by setting content + state and nothing else;
// `DocArea` renders `completed` as a read-only `doc-body`; `DocumentGenerationFlow` mounts
// ManualEditor only for `mode === 'manual'`, which `selectType` never sets on the create path.
//
// GENUINE RED — the transition does not exist. Unlike every step of scenario 1.2, this is not a
// coverage pin on shipped behaviour, and no bite verification stands in for a real failure: the
// failure below was observed live before the marker went on.
vi.mock('../../features/generation/api/generationApi')
vi.mock('../../features/generation/api/documentApi')

const TOPIC = 'Влияние ИИ на образование'
const GENERATION_ID = 'gen-2-1'
const GENERATED_TEXT = 'Готовый текст доклада'

describe('DocumentGenerationFlow — a completed generation opens itself in the editor', () => {
  beforeEach(() => {
    vi.mocked(api.createGeneration).mockResolvedValue({
      generationId: GENERATION_ID,
      status: 'pending',
    })
    // The first poll — `useGeneration.submit` fires one immediately — already observes completion,
    // so the whole scenario resolves inside this render with no timer advanced. The generating
    // state is 1.2's subject and is deliberately not re-pinned here.
    vi.mocked(api.getGeneration).mockResolvedValue({
      generationId: GENERATION_ID,
      status: 'completed',
      content: GENERATED_TEXT,
      topic: TOPIC,
      volumePages: 5,
      documentType: 'доклад',
      createdAt: '2026-07-29T10:00:00Z',
    })
    // Never settles: whatever green does about persisting the converted document, this test must
    // not depend on it resolving. The claim under test is that the EDITOR SURFACE arrives by
    // itself — not what the document endpoint says afterwards.
    vi.mocked(documentApi.createDocument).mockReturnValue(new Promise(() => {}))
    vi.mocked(documentApi.getDocument).mockReturnValue(new Promise(() => {}))
    window.history.pushState({}, '', '/')
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
  })

  afterEach(() => {
    clearSession()
    vi.clearAllMocks()
  })

  // The RED this was written against, observed 2026-07-29 (1 failed), at the `findByTestId` below:
  //
  //   TestingLibraryElementError: Unable to find an element by: [data-testid="manual-editor"]
  //
  // The printed DOM is the diagnosis in full: `<div class="doc-body markdown-body"
  // data-testid="doc-body"><p>Готовый текст доклада</p></div>` beside a `Создать новый доклад`
  // button. The generation completed, the text arrived, and the surface stayed read-only — there
  // is no code path from `state === 'completed'` to the editor. That path now exists.
  //
  // EVERYTHING BELOW THE `findByTestId` IS UNREACHABLE IN TODAY'S CODEBASE, so — as d4f34b7 did
  // for its en-dash risk — the assertions were executed elsewhere rather than trusted. A
  // throwaway test mounted `ManualEditor` directly on the history-open shape (getDocument
  // resolving `GENERATED_TEXT`) and PASSED, 2026-07-29, on: `manual-editor`,
  // `editor-content-area` + `contenteditable="true"`, `editor-breadcrumb` existing and reading
  // exactly `Доклад · Ручной режим` (which proves the Cyrillic `Доклад` typed below is the real
  // string, and that `/^Доклад$/` genuinely fails today), the content assertion's `waitFor` form
  // against `GENERATED_TEXT`, both absence checks, and `createDocument` not-called. The scratch
  // was deleted. STILL UNVERIFIED, and unverifiable before green: that these hold on the AUTO
  // path (no such path exists), and the two `getGeneration` counts, which depend on a transition
  // that has not been written.
  it('replaces the read-only result with the editor without a further gesture', async () => {
    render(<App />)

    fireEvent.click(screen.getByTestId('features-primary-cta-button'))
    fireEvent.click(screen.getByTestId('type-card-doklad'))
    fireEvent.change(screen.getByTestId('topic-input'), { target: { value: TOPIC } })

    // The LAST user gesture in this test. Every assertion below runs against a page nobody
    // touched again — that is the "no extra click" half of the scenario, and it is load-bearing:
    // a green that adds an "Открыть в редакторе" button satisfies the surface assertion only if
    // this file is edited, which is what makes the absence of a further fireEvent an assertion
    // rather than an omission.
    fireEvent.click(screen.getByTestId('topic-send'))

    expect(api.createGeneration).toHaveBeenCalledTimes(1)
    expect(api.createGeneration).toHaveBeenCalledWith(TOPIC, 'doklad')

    // The editor shell is lazy (Tiptap), so this await covers a real chunk load, not just a state
    // flush. This is where the RED throws.
    const editor = await screen.findByTestId('manual-editor')

    // Deliberately NOT `expect(editor).toBeInTheDocument()` — `findByTestId` already throws when
    // the node is absent, so that line asserts nothing `await` has not already asserted, and the
    // pair together are satisfied by an empty `<div data-testid="manual-editor" />`. What makes
    // the surface an EDITOR rather than the completed view wearing the editor's name is that it
    // accepts typing without a further action: `contenteditable` by equality, not truthiness.
    // This is the renderer-side twin of the same fix the 2.1 Selenium contract took.
    const contentArea = within(editor).getByTestId('editor-content-area')
    expect(contentArea).toHaveAttribute('contenteditable', 'true')

    // The editor must open for the type the user picked, and the breadcrumb is where it says so.
    // This equality and the Selenium contract's `EXPECTED_AUTO_EDITOR_BREADCRUMB = "Доклад"` are
    // PARALLEL HAND-MAINTAINED PINS, not linked ones: that constant is Python in
    // `acceptance/statements/`, this is an independently typed `/^Доклад$/`, and a TS file cannot
    // import it. Change one and the other keeps asserting the old string in silence — the exact
    // hazard `frontend/src/shared/documentTypes.ts` names ("two hand-maintained tables are two
    // chances to disagree, and the disagreement would be silent"). Edit both or neither.
    //
    // What green owes in `ManualEditorBreadcrumb.tsx`, stated precisely because the wrong reading
    // breaks a live test: today those chips render `Доклад · Ручной режим`, and on THIS path the
    // hardcoded `Ручной режим` chip and the `me-breadcrumb-sep` beside it must not render. Make
    // the mode chip CONDITIONAL — do NOT delete it. `useFlowNavigation.ts` records that story 18
    // dropped the modal so `mode` is always 'auto' on the create path, but 'manual' survives on
    // the history-open path (`openDocumentFromHistory`), and that path is under a live,
    // un-skipped assertion: `manual_editor_statements.EXPECTED_DOKLAD_BREADCRUMB =
    // "Доклад · Ручной режим"`, consumed by `test_manual_editor_acceptance.py`. That constant
    // must keep passing. Deleting the chip outright turns this one-second failure into a
    // three-layers-away break in a suite green may not edit.
    //
    // Honest about its limits: `doklad` is the only `available: true` card, so a green that
    // hardcodes the default satisfies this. That arm is owned by the sibling
    // `DocumentGenerationFlow.documentType.test.tsx` and the wire test, not by this file.
    expect(within(editor).getByTestId('editor-breadcrumb')).toHaveTextContent(/^Доклад$/)

    // THE GENERATED TEXT SURVIVES THE TRANSITION. Without this, every other assertion here is
    // satisfied by an editor mounted EMPTY — and the `doc-body` absence below actively removes
    // the last surface still showing the text, so a cosmetically-passing green is data loss:
    // "it deleted my report". `GENERATED_TEXT` was only the poll payload; nothing read it back.
    //
    // The red-agent's objection, weighed and overruled: it argued this forces a mechanism
    // decision in RED, because `vi.mock` auto-mocking only stubs EXISTING exports, so a
    // green-added `createDocumentFromGeneration` would return `undefined` and fail this for an
    // unrelated reason. It does not survive: the assertion is about the DOM after the transition,
    // which green must reach by whatever mechanism it picks, and green owns adding its own mock.
    // Deferring left a window where a blank editor is fully green — red-frontend-api's seam by
    // its own header cannot see a surface, and the Selenium class is skipped.
    //
    // The second wait in the test, and it is not the same wait as above: `manual-editor` is the
    // shell arriving, this is content landing inside it afterwards.
    await waitFor(() => expect(contentArea).toHaveTextContent(GENERATED_TEXT))

    // The completed generation's read-only render is DocArea's `doc-body`. Asserting its absence
    // is what makes this a REPLACEMENT rather than an addition: an editor mounted while the
    // read-only copy is still on screen shows the user the same text twice, and leaves them to
    // work out which one accepts typing.
    expect(screen.queryByTestId('doc-body')).toBeNull()
    expect(screen.queryByTestId('generation-generating')).toBeNull()

    // The status check the transition ran on: asked for the run that was actually created, and
    // asked once. The first poll — fired by `submit` the instant the POST resolves — already
    // returns `completed`, so a second call means the transition re-read what it was already
    // holding, which scenario 2.3 exists to forbid. Polling the wrong id renders another run's
    // document and every assertion above still passes.
    //
    // What this CANNOT see, stated so nobody reads more into it: the 5s `POLL_INTERVAL_MS` never
    // elapses inside this test (real timers, milliseconds of wall clock), so a poll loop that
    // outlived its own result is invisible here — and so is it to the `generation-generating`
    // absence above, which the surface swap guarantees whether or not `stopPolling` ran.
    //
    // POLL-LOOP TEARDOWN HAS NO EXECUTED GUARD IN ANY SUITE. The earlier note here nominated the
    // Selenium `assert_the_poll_loop_stopped`; that class is `@pytest.mark.skip` AND no CI
    // workflow runs `acceptance/` at all, so the nominated owner is nominal twice over. The
    // incident is not only load: a late poll resolving after the user starts typing has
    // `runPollAttempt` call `setContent` again and overwrite their edits mid-sentence. The
    // fake-timer arm that would close it here (advance past `POLL_INTERVAL_MS` after the editor
    // mounts, assert `getGeneration` is still at 1) needs the editor to MOUNT first, so it is
    // unwritable until the transition exists. It is owed by green, in this file.
    expect(api.getGeneration).toHaveBeenCalledWith(GENERATION_ID)
    expect(api.getGeneration).toHaveBeenCalledTimes(1)

    // The generation path must not mint a SECOND, empty document. With no `existingDocumentId`,
    // `useDocumentInit` fires `createDocument(documentType, key)` on mount — one generation, two
    // documents, and the user's edits land in the one the generation is not in. The stubs above
    // never settle, so without this line green can also ship the other shape: conversion wired
    // but no `documentId` resolved, whose consequence `useDocumentInit`'s own comment states —
    // "handleSave returns on its first line, so the Save button becomes a permanent no-op and the
    // status line sits on 'Создание документа…' forever". This file cannot tell that state from
    // correct wiring; it can and does forbid the first shape outright.
    expect(documentApi.createDocument).not.toHaveBeenCalled()
  })
})
