import { vi } from 'vitest'
import * as api from '../../features/generation/api/generationApi'
import * as documentApi from '../../features/generation/api/documentApi'
import { saveSession } from '../../features/auth/utils/authSession'

// The arming half of DocumentGenerationFlow.autoEditorTransition.test.tsx, split out under the
// 200-line file cap. `vi.mock` stays in the test file — it is hoisted per module and cannot be
// registered from here — so this module only ever reads mocks the caller has already registered,
// the same arrangement as ManualEditor.autosaveFixture.ts.
export const TOPIC = 'Влияние ИИ на образование'
export const GENERATION_ID = 'gen-2-1'
export const GENERATED_TEXT = 'Готовый текст доклада'

export function armCompletedGeneration() {
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
  // Never settles: whatever green does about persisting the converted document, the test must not
  // depend on it resolving. The claim under test is that the EDITOR SURFACE arrives by itself —
  // not what the document endpoint says afterwards.
  vi.mocked(documentApi.createDocument).mockReturnValue(new Promise(() => {}))
  vi.mocked(documentApi.getDocument).mockReturnValue(new Promise(() => {}))
  // The conversion green wired: the auto path turns the generation into a Document and adopts the
  // SERVER's HTML. Left unstubbed it resolves `undefined` under the module auto-mock and the hook
  // rejects on the missing fields. It resolves the same text so the content assertion stays about
  // the TRANSITION rather than about markdown conversion, which the backend's suite pins.
  vi.mocked(documentApi.createDocumentFromGeneration).mockResolvedValue({
    documentId: 'doc-2-1',
    generationId: GENERATION_ID,
    title: TOPIC,
    status: 'draft',
    content: `<p>${GENERATED_TEXT}</p>`,
    version: 1,
  })
  window.history.pushState({}, '', '/')
  saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
}
