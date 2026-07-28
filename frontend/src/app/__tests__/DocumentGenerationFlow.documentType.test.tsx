import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import App from '../App'
import * as api from '../../features/generation/api/generationApi'
import * as documentApi from '../../features/generation/api/documentApi'
import { clearSession, saveSession } from '../../features/auth/utils/authSession'

// Story 18, scenario 1.1 — the RENDER-level half of "the type the user picked is the type that
// gets generated".
//
// `useFlowNavigation.documentType.test.tsx` drives the join on the hook directly, and
// `generationApi.documentType.test.ts` pins the wire. Neither one sees the single production
// edge that connects the join to the UI: `onSubmit={flow.submitGeneration}` in
// DocumentGenerationFlow. Rewiring that prop back to `flow.generation.submit` is neither a type
// error (both new parameters are optional-with-default, so the narrower signature is still
// structurally assignable to ChatWorkspace's `onSubmit: (topic: string) => void`) nor a failure
// in any other test — every card would silently generate a доклад again with a fully green
// suite. This file closes that last gap by clicking the real path and asserting the API call.
vi.mock('../../features/generation/api/generationApi')
vi.mock('../../features/generation/api/documentApi')

const TOPIC = 'Влияние ИИ на образование'

describe('DocumentGenerationFlow — the workspace submits the picked type, not just the topic', () => {
  beforeEach(() => {
    vi.mocked(api.createGeneration).mockReturnValue(new Promise(() => {}))
    vi.mocked(documentApi.createDocument).mockReturnValue(new Promise(() => {}))
    window.history.pushState({}, '', '/')
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
  })

  afterEach(() => {
    clearSession()
    vi.clearAllMocks()
  })

  // 'doklad' is the only card with `available: true` in shared/documentTypes.ts, so it is the
  // only type a click can produce today. The assertion still bites: the defect this guards
  // against drops the SECOND argument entirely, and an exact two-argument
  // toHaveBeenCalledWith fails against a one-argument call regardless of which type it is.
  it('sends the topic AND the document type picked on the type card', () => {
    render(<App />)

    fireEvent.click(screen.getByTestId('features-primary-cta-button'))
    fireEvent.click(screen.getByTestId('type-card-doklad'))

    fireEvent.change(screen.getByTestId('topic-input'), { target: { value: TOPIC } })
    fireEvent.click(screen.getByTestId('topic-send'))

    expect(api.createGeneration).toHaveBeenCalledTimes(1)
    expect(api.createGeneration).toHaveBeenCalledWith(TOPIC, 'doklad')
  })
})
