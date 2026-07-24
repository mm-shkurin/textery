import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useFlowNavigation } from '../useFlowNavigation'
import { clearSession, saveSession } from '../../features/auth/utils/authSession'

const navigate = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => navigate }
})

vi.mock('../../features/generation/api/generationApi')

function wrapper({ children }: { children: ReactNode }) {
  return <MemoryRouter>{children}</MemoryRouter>
}

function renderFlow() {
  return renderHook(() => useFlowNavigation(), { wrapper })
}

describe('useFlowNavigation', () => {
  beforeEach(() => {
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
  })

  afterEach(() => {
    clearSession()
    vi.clearAllMocks()
  })

  it('starts on the landing step', () => {
    const { result } = renderFlow()

    expect(result.current.step).toBe('landing')
  })

  // "Try it free" answered with a password prompt asks for a password the visitor does not have
  // yet, so an anonymous CTA click goes to register — and must NOT advance the flow behind it.
  it('sends an anonymous visitor to register instead of opening the type step', () => {
    clearSession()
    const { result } = renderFlow()

    act(() => result.current.startFlow())

    expect(navigate).toHaveBeenCalledWith('/register')
    expect(result.current.step).toBe('landing')
  })

  it('opens the type step for a signed-in visitor', () => {
    const { result } = renderFlow()

    act(() => result.current.startFlow())

    expect(result.current.step).toBe('type')
  })

  it('carries the sign-in destination so the user returns to what they were doing', () => {
    const { result } = renderFlow()

    act(() => result.current.goToLogin())

    expect(navigate).toHaveBeenCalledWith('/login', { state: { from: '/' } })
  })

  it('walks type then mode into the form', () => {
    const { result } = renderFlow()

    act(() => result.current.selectType('doklad'))
    expect(result.current.step).toBe('mode')

    act(() => result.current.selectMode('auto'))
    expect(result.current.step).toBe('form')
    expect(result.current.documentType).toBe('doklad')
    expect(result.current.mode).toBe('auto')
  })

  it('steps back to the type and landing screens', () => {
    const { result } = renderFlow()

    act(() => result.current.selectType('doklad'))
    act(() => result.current.backToTypeModal())
    expect(result.current.step).toBe('type')

    act(() => result.current.backToLanding())
    expect(result.current.step).toBe('landing')
  })

  it('opens the history screen', () => {
    const { result } = renderFlow()

    act(() => result.current.openHistory())

    expect(result.current.step).toBe('history')
  })

  // The document id is what tells the editor to GET an existing document rather than POST a new
  // one, and an unrecognised wire type must not block opening it — the label falls back, the
  // content still comes from the GET.
  it('opens a document from history, falling back on an unfamiliar type label', () => {
    const { result } = renderFlow()

    act(() => result.current.openDocumentFromHistory('doc-1', 'нечто-невиданное'))

    expect(result.current.step).toBe('form')
    expect(result.current.mode).toBe('manual')
    expect(result.current.openDocumentId).toBe('doc-1')
    expect(result.current.documentType).toBe('doklad')
  })

  // Back goes to wherever the editor was opened FROM. A history-opened document returned to the
  // mode modal would offer to pick a mode for a document that already has one.
  it('returns a history-opened document to history, not to the mode modal', () => {
    const { result } = renderFlow()

    act(() => result.current.openDocumentFromHistory('doc-1', 'Доклад'))
    act(() => result.current.backFromEditor())

    expect(result.current.step).toBe('history')
    expect(result.current.openDocumentId).toBeNull()
    expect(result.current.mode).toBeNull()
  })

  it('returns a newly created document to the mode modal', () => {
    const { result } = renderFlow()

    act(() => result.current.selectType('doklad'))
    act(() => result.current.selectMode('manual'))
    act(() => result.current.backFromEditor())

    expect(result.current.step).toBe('mode')
    expect(result.current.mode).toBeNull()
  })

  // Signing out has to unwind the flow, not just the header: leaving `step` at 'form' would keep
  // a generation polling and drop the next user straight back into the workspace.
  it('unwinds the whole flow on sign-out', () => {
    const { result } = renderFlow()

    act(() => result.current.selectType('doklad'))
    act(() => result.current.selectMode('manual'))
    act(() => result.current.handleLogout())

    expect(result.current.step).toBe('landing')
    expect(result.current.documentType).toBeNull()
    expect(result.current.mode).toBeNull()
    expect(result.current.openDocumentId).toBeNull()
    expect(result.current.isAuthenticated).toBe(false)
  })

  it('clears every selection when the flow is closed', () => {
    const { result } = renderFlow()

    act(() => result.current.openDocumentFromHistory('doc-1', 'Доклад'))
    act(() => result.current.closeToLanding())

    expect(result.current.step).toBe('landing')
    expect(result.current.documentType).toBeNull()
    expect(result.current.openDocumentId).toBeNull()
  })
})
