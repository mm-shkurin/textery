import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useFlowNavigation } from '../useFlowNavigation'
import * as api from '../../features/generation/api/generationApi'
import { clearSession, saveSession } from '../../features/auth/utils/authSession'

// Story 18, scenario 1.1 — the caller-level half of "the type the user picked is the type that
// gets generated".
//
// `generationApi.documentType.test.ts` pins the WIRE: given a document type, createGeneration
// sends the right Cyrillic value. That test passes even if nothing ever hands it a type, because
// the parameter defaults to DEFAULT_DOCUMENT_TYPE — so on its own it proves the translation and
// not the thread-through, and the real defect (every card generating a доклад) would survive a
// fully green suite. This file closes that gap one layer up: it drives the production join
// (`selectType` stores the type, `submitGeneration` carries it to the API) and asserts the API
// was CALLED with the picked type.
//
// 'referat' rather than the default on purpose: with 'doklad' the assertion would pass against
// the hardcoded value it exists to rule out. It is not reachable through the type modal today
// (`available: false` in shared/documentTypes.ts), which is exactly why the guard belongs at
// this seam rather than in a click-driven test.
vi.mock('../../features/generation/api/generationApi')

const navigate = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => navigate }
})

function wrapper({ children }: { children: ReactNode }) {
  return <MemoryRouter>{children}</MemoryRouter>
}

describe('useFlowNavigation — the picked document type reaches the generation request', () => {
  beforeEach(() => {
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
    vi.mocked(api.createGeneration).mockResolvedValue({ generationId: 'gen-1', status: 'pending' })
    vi.mocked(api.getGeneration).mockResolvedValue({
      generationId: 'gen-1',
      status: 'pending',
      content: null,
      topic: 'Тема',
      volumePages: 5,
      documentType: 'реферат',
      createdAt: '2026-07-28T00:00:00Z',
    })
  })

  afterEach(() => {
    clearSession()
    vi.clearAllMocks()
  })

  it('submits the type chosen on the type card, not the default', async () => {
    const { result } = renderHook(() => useFlowNavigation(), { wrapper })

    act(() => result.current.selectType('referat'))
    await act(async () => {
      result.current.submitGeneration('Тема')
    })

    // Both arguments, exactly once: a second POST is a second billed generation, and asserting
    // the topic alongside the type stops a future refactor from swapping the parameter order
    // and still "passing".
    expect(api.createGeneration).toHaveBeenCalledTimes(1)
    expect(api.createGeneration).toHaveBeenCalledWith('Тема', 'referat')
  })
})
