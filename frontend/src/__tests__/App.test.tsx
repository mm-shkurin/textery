import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import App from '../App'
import * as api from '../features/generation/api/generationApi'
import { saveSession, clearSession } from '../features/auth/utils/authSession'

vi.mock('../features/generation/api/generationApi')

// These tests exercise the generation flow, which is now behind a session: the landing stays
// public, but its CTA sends an anonymous visitor to /login instead of opening the type modal.
// Signing in is therefore setup, not subject — without it every test below stops at the
// landing. (They passed before this because the flow was open to anonymous users; that changed
// by product decision, not by accident.)
describe('App step transitions', () => {
  beforeEach(() => {
    vi.mocked(api.createGeneration).mockReturnValue(new Promise(() => {}))
    // App renders its own BrowserRouter, and jsdom's location SURVIVES between tests in a
    // file — so the gate test below, which navigates to /login, would otherwise leave every
    // later render starting there. Reset the URL, not just the session.
    window.history.pushState({}, '', '/')
    saveSession({ accessToken: 'test-access-token', refreshToken: 'test-refresh-token' })
  })

  afterEach(() => {
    clearSession()
  })

  it('sends an anonymous visitor to the login page instead of opening the flow', () => {
    // The gate this pins is the ONLY reachable path into the workspace: it has no URL of its
    // own, so the CTA is the door. Without this test, deleting the gate breaks nothing visible.
    clearSession()
    render(<App />)

    fireEvent.click(screen.getByTestId('features-primary-cta-button'))

    expect(screen.queryByTestId('type-modal')).not.toBeInTheDocument()
    expect(screen.getByTestId('login-submit-button')).toBeInTheDocument()
  })

  it('keeps the landing itself open to an anonymous visitor', () => {
    clearSession()
    render(<App />)

    expect(screen.getByTestId('features-primary-cta-button')).toBeInTheDocument()
  })

  it('walks landing -> type -> mode -> form and back to landing on close', () => {
    render(<App />)

    fireEvent.click(screen.getByTestId('features-primary-cta-button'))
    expect(screen.getByTestId('type-modal')).toBeInTheDocument()

    fireEvent.click(screen.getByTestId('type-card-doklad'))
    expect(screen.getByTestId('mode-modal')).toBeInTheDocument()

    fireEvent.click(screen.getByTestId('mode-card-auto'))
    expect(screen.getByTestId('chat-panel')).toBeInTheDocument()
  })

  it('back button from mode modal returns to type modal', () => {
    render(<App />)

    fireEvent.click(screen.getByTestId('features-primary-cta-button'))
    fireEvent.click(screen.getByTestId('type-card-doklad'))
    expect(screen.getByTestId('mode-modal')).toBeInTheDocument()

    fireEvent.click(screen.getByLabelText(/Назад к типу документа/))
    expect(screen.getByTestId('type-modal')).toBeInTheDocument()
  })

  it('closing the type modal returns to landing', () => {
    render(<App />)

    fireEvent.click(screen.getByTestId('features-primary-cta-button'))
    fireEvent.click(screen.getByLabelText('Закрыть'))

    expect(screen.queryByTestId('type-modal')).not.toBeInTheDocument()
  })
})
