import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { App } from '../App'
import * as api from '../../features/generation/api/generationApi'
import * as documentApi from '../../features/generation/api/documentApi'
import { clearSession, saveSession } from '../../shared/session/authSession'
import { EMPTY_PARAMETERS } from '../../features/generation/utils/generationParameters'

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
    // The parameters object travels with the topic: these tests drive the real
    // Composer, so an untouched form sends its defaults rather than nothing. Asserted
    // by value — a client that dropped the argument would still call with two.
    expect(api.createGeneration).toHaveBeenCalledWith(TOPIC, 'doklad', EMPTY_PARAMETERS)
  })

  // A second Ctrl+Enter on the same topic bills the user twice: createGeneration mints a fresh
  // crypto.randomUUID() per call, and that Idempotency-Key is scoped to the internal 401-replay,
  // so two user-initiated submits carry two different keys and the backend cannot collapse them.
  // The first generation then runs to completion unwatched, because the client polls the second.
  //
  // Nothing guards this deliberately. The send BUTTON is disabled only on a blank topic, never
  // while a request is in flight, and Composer's onKeyDown has no in-flight check either. What
  // actually stops the second dispatch today is render ordering: useGeneration.submit sets state
  // to 'pending' synchronously, which swaps Composer for Progress before the next event is
  // delivered. That is emergent, not asserted — moving setState('pending') behind the awaited
  // createGeneration, or keeping Composer mounted during pending, silently reopens it.
  it('bills one generation for a double Ctrl+Enter, not two', () => {
    render(<App />)

    fireEvent.click(screen.getByTestId('features-primary-cta-button'))
    fireEvent.click(screen.getByTestId('type-card-doklad'))

    const input = screen.getByTestId('topic-input')
    fireEvent.change(input, { target: { value: TOPIC } })
    fireEvent.keyDown(input, { key: 'Enter', ctrlKey: true })
    fireEvent.keyDown(input, { key: 'Enter', ctrlKey: true })

    expect(api.createGeneration).toHaveBeenCalledTimes(1)
  })
})
